"""Runs one benchmark across many machines, e.g. as a GitHub Actions matrix (.github/workflows/benchmark.yml).

Every machine runs one shard: a disjoint slice of one client × anticheat pair's trials with its own server, bot and
target bot. Two stages keep the screening of the local runner: first the reference shards ("none"), then the
anticheat shards, which only repeat the variants that showed an effect in the reference. Per stage, the shards are
spread over the available machines so that all of them finish at about the same time.

Hand-over between machines happens through tarballs of results/<run>/: `matrix` packs the pair plans and run.json,
`shard` packs its shard folder, `collect` unpacks everything, merges the shard status into run.json and analyzes.

Pairs whose inputs did not change are not measured again. Every pair gets a key over everything that decides its
measurement (see pair_key); `collect` keeps the raw data of every cleanly measured pair in a store (the Actions cache
in CI), and `matrix` takes a pair with a known key from there instead of planning shards for it. A reused reference
also keeps the screening: the anticheat stage reads it just like a freshly measured one.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

from .analyze import REFERENCE_AC, analyze_run, trial_rows
from .config import AntiCheat, Benchmark, Client
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


# Plan fields that differ between runs without changing what is measured.
_RUN_SPECIFIC = ("run_id", "progress_file", "client_log", "modules_dump", "server_address")
# Sources whose changes alter the measurement itself: driver mod, collector plugin and the process setup.
_MEASUREMENT_CODE = ("driver-mod", "collector-plugin", "orchestrator/acbench/processes.py")
_IGNORED_DIRS = {"build", ".gradle", "run"}


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_ADAPTER_DIR = "driver-mod/src/main/java/dev/acbench/driver/adapter/"
# Adapters every pair uses: the interface, and NoneAdapter, which drives the target bot.
_SHARED_ADAPTERS = {"CheatClientAdapter.java", "NoneAdapter.java"}


def _counts_for(name: str, adapter: str) -> bool:
    """Other clients' adapters and the registry that lists them do not change this client's measurement, so adding
    a client keeps the keys of all existing pairs. A client's own adapter is <Adapter>Adapter.java by convention."""
    if not name.startswith(_ADAPTER_DIR) or "/" in name[len(_ADAPTER_DIR):]:
        return True
    file = name[len(_ADAPTER_DIR):]
    return file in _SHARED_ADAPTERS or file.lower() == f"{adapter.lower()}adapter.java"


def _code_hash(root: Path, adapter: str) -> str:
    """Hash of the measurement sources rather than of the built jars, which Gradle does not build byte-identically.
    Only files under version control count, so build output never changes the key."""
    try:
        listed = subprocess.run(["git", "ls-files", "-z", "--", *_MEASUREMENT_CODE], cwd=root, check=True,
                                capture_output=True).stdout.decode().split("\0")
        files = sorted(root / name for name in listed if name)
    except (OSError, subprocess.CalledProcessError):
        files = sorted(p for entry in _MEASUREMENT_CODE for p in ([root / entry] if (root / entry).is_file()
                       else (root / entry).rglob("*")) if p.is_file() and not _IGNORED_DIRS & set(p.relative_to(root).parts))
    digest = hashlib.sha256()
    for path in files:
        if path.exists() and _counts_for(path.relative_to(root).as_posix(), adapter):
            digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def pair_key(runner: Runner, client: Client, ac: AntiCheat, plan: dict) -> str:
    """Everything that decides one pair's measurement: the trial list and timing (the plan without run-specific
    paths), the exact jars of server, client and anticheat, the anticheat's flag sources, config files and target bot
    exemption, the server and client settings and the measurement code. Analysis-only settings (scoring, default
    alerts) are left out, so changing them re-analyzes instead of re-measuring."""
    bench = runner.bench
    inputs = {
        "plan": {k: v for k, v in plan.items() if k not in _RUN_SPECIFIC},
        "minecraft": bench.minecraft, "server": bench.server, "client_settings": bench.client,
        "client": {"jvm_args": client.jvm_args, "adapter": client.adapter, "adapter_options": client.adapter_options,
                   "always_disable": client.always_disable},
        "anticheat": {"plugin": ac.plugin, "flag_sources": ac.flag_sources,
                      "target_bypass_permissions": ac.target_bypass_permissions,
                      "files": {target: _file_hash(source) for target, source in sorted(ac.files.items())}},
        "jars": {jar.name: _file_hash(jar) for jar in [runner.paper_jar, *runner.client_jars[client.id], *runner.ac_jars[ac.id]]},
        "code": _code_hash(bench.root, client.adapter),
    }
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, default=str).encode()).hexdigest()[:24]


class PairStore:
    """Raw data of measured pairs by key: <store>/<client>/<anticheat>/<key>.tgz plus a .json with its origin."""

    def __init__(self, root: Path):
        self.root = root

    def _base(self, client_id: str, ac_id: str, key: str) -> Path:
        return self.root / client_id / ac_id / key

    def get(self, client_id: str, ac_id: str, key: str) -> tuple[Path, dict] | None:
        base = self._base(client_id, ac_id, key)
        tar_file, info = base.with_suffix(".tgz"), base.with_suffix(".json")
        if not tar_file.exists():
            return None
        return tar_file, json.loads(info.read_text()) if info.exists() else {}

    def put(self, run_dir: Path, client_id: str, ac_id: str, key: str, info: dict) -> None:
        base = self._base(client_id, ac_id, key)
        base.parent.mkdir(parents=True, exist_ok=True)
        _pack(base.with_suffix(".tgz"), run_dir, [run_dir / client_id / ac_id])
        base.with_suffix(".json").write_text(json.dumps({**info, "stored": time.time()}, indent=1))

    def prune(self, keep: int = 2) -> None:
        """Keeps the newest `keep` keys per pair: older ones belong to client or anticheat versions no longer tested."""
        for pair_dir in self.root.glob("*/*"):
            infos = sorted(pair_dir.glob("*.json"), key=lambda p: json.loads(p.read_text()).get("stored", 0), reverse=True)
            for info in infos[keep:]:
                info.unlink()
                info.with_suffix(".tgz").unlink(missing_ok=True)


def _unmeasured(pair_dir: Path, client_id: str, ac_id: str) -> int:
    """Trials of a pair's shards without a measurement and without an anticheat kick."""
    lost = 0
    for unit in sorted(p.parent for p in pair_dir.glob("shards/*/plan.json")) or [pair_dir]:
        lost += trial_rows(unit, client_id, ac_id, 0)[1]["unmeasured"]
    return lost


def _restrict(bench: Benchmark, client_id: str) -> Benchmark:
    return dataclasses.replace(bench, client_ids=[client_id], clients={client_id: bench.clients[client_id]},
                               anticheats=dict(bench.anticheats), anticheat_ids=list(bench.anticheat_ids))


def matrix(bench: Benchmark, run_id: str, stage: str, artifacts: dict[str, Path], scenario_filter: set[str] | None,
           slots: int | None, tar_file: Path, install: bool = False, discover_missing: bool = False,
           store: PairStore | None = None) -> list[dict]:
    """Writes the plans of one stage's pairs, packs them with run.json into `tar_file` and returns the job matrix.
    Pairs found in `store` come along with their data instead of getting shards.
    The anticheat stage expects the reference shards of the same run to be unpacked into results/<run>/ already."""
    if discover_missing:
        # Variants generated from a client's module dump (auto_modes) only exist once the dump does.
        for client_id in bench.client_ids:
            if not module_dump_file(bench, bench.clients[client_id]).exists():
                print(f"[ci] {client_id}: no module dump yet, discovering")
                discover(_restrict(bench, client_id), artifacts)
    runner = Runner(bench, run_id, scenario_filter, artifacts, 1)
    meta_file = runner.run_dir / "run.json"
    earlier = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    runner.prepare(install=install)
    keys, reused = dict(earlier.get("pair_keys", {})), dict(earlier.get("reused", {}))
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
            plan = json.loads((out / "plan.json").read_text())
            pair = f"{client.id}/{ac.id}"
            keys[pair] = pair_key(runner, client, ac, plan)
            found = store.get(client.id, ac.id, keys[pair]) if store else None
            if found:
                tar_file_found, info = found
                shutil.rmtree(out)
                with tarfile.open(tar_file_found) as tar:
                    tar.extractall(runner.run_dir, filter="data")
                # Plan and default alert thresholds of this run; the raw data is identical by construction of the key.
                runner.write_pair(client, ac, trials)
                lost = _unmeasured(out, client.id, ac.id)
                if lost:
                    # Stored before incomplete pairs were kept out of the store: measure it again.
                    print(f"[ci] {pair}: stored data from {info.get('run')} misses {lost} trials, measuring again")
                    shutil.rmtree(out)
                    out = runner.write_pair(client, ac, trials)
                else:
                    reused[pair] = {"key": keys[pair], "run": info.get("run")}
                    written.append(out)
                    print(f"[ci] {pair}: unchanged since {info.get('run')}, reusing its {len(trials)} trials")
                    continue
            written += [out / "plan.json", out / "anticheat.json"]
            pairs[(client.id, ac.id)] = (len(trials), estimate_seconds(plan))
    runner.meta.update(pair_keys=keys, reused=reused)
    runner.save_meta()
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


def collect(run_dir: Path, tar_files: list[Path], store: PairStore | None = None) -> bool:
    """Unpacks plan and shard tarballs (plans first: the anticheat stage's run.json supersedes the reference one),
    merges every shard's status into run.json, writes the reports and keeps every freshly and cleanly measured pair in
    `store`. Returns whether every shard finished."""
    root = run_dir.parent.parent
    meta_file = run_dir / "run.json"
    pair_keys, reused = {}, {}
    for tar_file in sorted(tar_files, key=lambda p: ("plan-reference" not in p.name, "plan-" not in p.name, p.name)):
        with tarfile.open(tar_file) as tar:
            tar.extractall(root, filter="data")
        # Each stage's run.json knows its own pairs; keep them all, whatever order the tarballs come in.
        if meta_file.exists():
            stage_meta = json.loads(meta_file.read_text())
            pair_keys.update(stage_meta.get("pair_keys", {}))
            reused.update(stage_meta.get("reused", {}))
    meta = json.loads(meta_file.read_text())
    meta.update(pair_keys=pair_keys, reused=reused)
    meta["status"] = {}
    shard_dirs = sorted(run_dir.glob("*/*/shards/s*"))
    for unit in shard_dirs:
        status_file = unit / "status.json"
        status = json.loads(status_file.read_text()) if status_file.exists() else {"finished": False, "error": "no status"}
        meta["status"].setdefault(f"{unit.parent.parent.parent.name}/{unit.parent.parent.name}", {})[unit.name] = status
    reused = meta.get("reused", {})
    meta["workers"] = sum(1 for unit in shard_dirs if f"{unit.parent.parent.parent.name}/{unit.parent.parent.name}" not in reused)
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2))
    result = analyze_run(run_dir)
    md, page = write_reports(result, run_dir)
    print(f"[ci] {len(shard_dirs)} shard(s) collected, {len(reused)} pair(s) reused; report: {md} / {page}")
    if store:
        for pair, key in meta.get("pair_keys", {}).items():
            info = result["runs"].get(pair) or {}
            # Only clean measurements are worth repeating forever: finished, every trial measured, not overloaded,
            # legal play unimpaired.
            clean = (info.get("done") and not info.get("unmeasured") and not (info.get("quality") or {}).get("overloaded")
                     and not (info.get("legal_play") or {}).get("invalid"))
            if pair in reused or not clean:
                continue
            client_id, ac_id = pair.split("/", 1)
            store.put(run_dir, client_id, ac_id, key, {"run": meta.get("run_id", run_dir.name)})
            print(f"[ci] {pair}: stored as {key}")
        store.prune()
    return all(s.get("finished") for pair in meta["status"].values() for s in pair.values())
