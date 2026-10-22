"""Runs one benchmark across many machines, e.g. as a GitHub Actions matrix (.github/workflows/benchmark.yml).

Every machine runs one shard: a disjoint slice of one client × anticheat pair's trials with its own server, bot and
target bot. Two stages keep the screening of the local runner: first the reference shards ("none"), then the
anticheat shards, which only repeat the variants that showed an effect in the reference. Per stage, the shards are
spread over the available machines so that all of them finish at about the same time.

Hand-over between machines happens through tarballs of results/<run>/: `matrix` packs the pair plans and run.json,
`shard` packs its shard folder, `collect` unpacks everything, merges the shard status into run.json and analyzes.
"""
from __future__ import annotations

import dataclasses
import json
import tarfile
import time
from pathlib import Path

from .analyze import REFERENCE_AC, analyze_run
from .config import Benchmark
from .plan import build_trials, estimate_seconds, module_dump_file
from .report import write_reports
from .runner import Job, LiveStatus, Runner, _screen, discover


def allocate(pairs: dict[str, tuple[int, float]], slots: int, min_trials: int) -> dict[str, int]:
    """Shards per pair for `slots` machines: repeatedly splits the pair whose shards currently take longest, so all
    shards end up about equally long. A shard never gets fewer than `min_trials` trials, because every shard pays the
    full start-up of server and clients. With more pairs than slots every pair is one shard and the queue balances."""
    shards = {key: 1 for key in pairs}
    caps = {key: max(1, trials // min_trials) for key, (trials, _) in pairs.items()}
    while sum(shards.values()) < slots:
        open_pairs = [key for key in pairs if shards[key] < caps[key]]
        if not open_pairs:
            break
        longest = max(open_pairs, key=lambda key: pairs[key][1] / shards[key])
        shards[longest] += 1
    return shards


def _pack(tar_file: Path, root: Path, paths: list[Path]) -> None:
    with tarfile.open(tar_file, "w:gz") as tar:
        for path in paths:
            tar.add(path, arcname=str(path.relative_to(root)))


def _restrict(bench: Benchmark, client_id: str) -> Benchmark:
    return dataclasses.replace(bench, client_ids=[client_id], clients={client_id: bench.clients[client_id]},
                               anticheats=dict(bench.anticheats), anticheat_ids=list(bench.anticheat_ids))


def matrix(bench: Benchmark, run_id: str, stage: str, artifacts: dict[str, Path], scenario_filter: set[str] | None,
           slots: int | None, tar_file: Path, install: bool = False, discover_missing: bool = False) -> list[dict]:
    """Writes the plans of one stage's pairs, packs them with run.json into `tar_file` and returns the job matrix.
    The anticheat stage expects the reference shards of the same run to be unpacked into results/<run>/ already."""
    if discover_missing:
        # Variants generated from a client's module dump (auto_modes) only exist once the dump does.
        for client_id in bench.client_ids:
            if not module_dump_file(bench, bench.clients[client_id]).exists():
                print(f"[ci] {client_id}: no module dump yet, discovering")
                discover(_restrict(bench, client_id), artifacts)
    runner = Runner(bench, run_id, scenario_filter, artifacts, 1)
    runner.prepare(install=install)
    reference = bench.anticheats.get(REFERENCE_AC)
    if stage == "reference":
        acs = [reference] if reference else []
    else:
        acs = [ac for ac in bench.anticheats.values() if ac.id != REFERENCE_AC]
    pairs, written = {}, [runner.run_dir / "run.json"]
    for client in bench.clients.values():
        all_trials = build_trials(bench, client, scenario_filter)
        for ac in acs:
            trials = all_trials
            if ac is not reference and reference and bench.timing.get("screen_variants", True):
                trials = _screen(runner.run_dir, client.id, ac.id, trials)
            out = runner.write_pair(client, ac, trials)
            written += [out / "plan.json", out / "anticheat.json"]
            plan = json.loads((out / "plan.json").read_text())
            pairs[(client.id, ac.id)] = (len(trials), estimate_seconds(plan))
    _pack(tar_file, bench.root, written)

    slots = slots or int(bench.parallel.get("ci_slots", 20))
    min_trials = int(bench.parallel.get("ci_min_trials_per_shard", 10))
    shards = allocate({key: value for key, value in pairs.items() if value[0]}, slots, min_trials)
    jobs = []
    for (client_id, ac_id), count in shards.items():
        trials, seconds = pairs[(client_id, ac_id)]
        for k in range(count):
            jobs.append({"client": client_id, "anticheat": ac_id, "shard": k, "of": count,
                         "trials": len(range(k, trials, count)), "minutes": round(seconds / count / 60, 1),
                         "name": f"{client_id} × {ac_id} {k + 1}/{count}"})
    # Longest shards first: GitHub starts matrix jobs roughly in order, so the short ones fill the gaps at the end.
    jobs.sort(key=lambda job: -job["minutes"])
    print(f"[ci] {stage}: {len(jobs)} shard(s) on {slots} slot(s), longest ~{max((j['minutes'] for j in jobs), default=0)} min "
          f"of trials each: " + ", ".join(f"{c}×{a}={n}" for (c, a), n in shards.items()))
    return jobs


def shard(bench: Benchmark, run_id: str, artifacts: dict[str, Path], k: int, of: int, tar_file: Path) -> bool:
    """Runs shard k of `of` of the single client × anticheat pair in `bench` and packs its folder into `tar_file`.
    The pair plan comes from the matrix stage, so every shard slices the same, already screened trial list."""
    client, ac = next(iter(bench.clients.values())), next(iter(bench.anticheats.values()))
    runner = Runner(bench, run_id, None, artifacts, 1)
    pair_dir = runner.run_dir / client.id / ac.id
    if not (pair_dir / "plan.json").exists():
        raise SystemExit(f"{pair_dir / 'plan.json'} missing: unpack the matrix stage's plan tarball first")
    trials = json.loads((pair_dir / "plan.json").read_text())["trials"][k::of]
    runner.prepare()
    live = LiveStatus(runner.run_dir, run_id, [(client.id, ac.id)], 1)
    job = Job(client, ac, k, of, pair_dir / "shards" / f"s{k}", trials)
    status = runner.run_shard(job, 0, live)
    live.update(state="finished" if status["finished"] else "failed", phase="finished", current=None)
    _pack(tar_file, bench.root, [job.unit_dir])
    return bool(status["finished"])


def collect(run_dir: Path, tar_files: list[Path]) -> bool:
    """Unpacks plan and shard tarballs (plans first: the anticheat stage's run.json supersedes the reference one),
    merges every shard's status into run.json and writes the reports. Returns whether every shard finished."""
    root = run_dir.parent.parent
    for tar_file in sorted(tar_files, key=lambda p: (not p.name.startswith("plan-reference"),
                                                     not p.name.startswith("plan-"), p.name)):
        with tarfile.open(tar_file) as tar:
            tar.extractall(root, filter="data")
    meta = json.loads((run_dir / "run.json").read_text())
    meta["status"] = {}
    shard_dirs = sorted(run_dir.glob("*/*/shards/s*"))
    for unit in shard_dirs:
        status_file = unit / "status.json"
        status = json.loads(status_file.read_text()) if status_file.exists() else {"finished": False, "error": "no status"}
        meta["status"].setdefault(f"{unit.parent.parent.parent.name}/{unit.parent.parent.name}", {})[unit.name] = status
    meta["workers"] = len(shard_dirs)
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2))
    result = analyze_run(run_dir)
    md, page = write_reports(result, run_dir)
    print(f"[ci] {len(shard_dirs)} shard(s) collected; report: {md} / {page}")
    return all(s.get("finished") for pair in meta["status"].values() for s in pair.values())
