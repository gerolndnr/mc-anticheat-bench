"""CLI: python -m acbench <build|fetch|plan|run|analyze> (run from the orchestrator/ directory or via ./bench)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import fetch
from .analyze import analyze_run
from .config import load_anticheat, load_benchmark, load_client
from .plan import build_plan, build_trials, estimate_seconds
from .report import write_reports
from .runner import discover, resolve_workers, run

ROOT = Path(__file__).resolve().parents[2]


def artifacts() -> dict[str, Path]:
    found = {
        "driver": sorted((ROOT / "driver-mod" / "build" / "libs").glob("acbench-driver-*.jar")),
        "collector": sorted((ROOT / "collector-plugin" / "build" / "libs").glob("acbench-collector-*.jar")),
    }
    missing = [k for k, v in found.items() if not v]
    if missing:
        sys.exit(f"Missing build output for {', '.join(missing)}; run './bench build' first")
    return {k: [j for j in v if "sources" not in j.name][-1] for k, v in found.items()}


def cmd_build(_args) -> None:
    gradle = os.environ.get("ACBENCH_GRADLE", "./gradlew")
    for project in ("driver-mod", "collector-plugin"):
        print(f"[build] {project}")
        subprocess.run([gradle, "build", "--no-daemon", "-q"], cwd=ROOT / project, check=True)
    print(json.dumps({k: str(v) for k, v in artifacts().items()}, indent=2))


def _filter(value: str | None) -> set[str] | None:
    return set(value.split(",")) if value else None


def _load(args):
    bench = load_benchmark(Path(args.config))
    if args.clients:
        bench.client_ids = args.clients.split(",")
        bench.clients = {k: bench.clients.get(k) or load_client(bench.config_dir / "clients" / f"{k}.toml") for k in bench.client_ids}
    if args.anticheats:
        wanted = args.anticheats.split(",")
        if "none" not in wanted:
            print("[warn] without the 'none' reference run no advantage/mitigation can be computed", file=sys.stderr)
        bench.anticheat_ids = wanted
        bench.anticheats = {k: bench.anticheats.get(k) or load_anticheat(bench.config_dir / "anticheats" / f"{k}.toml") for k in wanted}
    if args.reps:
        bench.repetitions = args.reps
    return bench


def cmd_fetch(args) -> None:
    bench = _load(args)
    cache = bench.root / "cache"
    print(fetch.paper(bench, cache))
    for client in bench.clients.values():
        print(fetch.client_mod(bench, client, cache, force=args.force))
    for ac in bench.anticheats.values():
        print(fetch.anticheat(bench, ac, cache, force=args.force))


def cmd_plan(args) -> None:
    bench = _load(args)
    for client in bench.clients.values():
        trials = build_trials(bench, client, _filter(args.scenarios))
        plan = build_plan(bench, client, "preview", trials, {"progress": "", "client_log": "", "modules_dump": ""})
        workers = resolve_workers(bench, getattr(args, "workers", None))
        print(f"{client.id}: {len(trials)} trials per anticheat, ~{estimate_seconds(plan) / 60:.0f} min each sequentially, "
              f"{len(bench.anticheats)} anticheats; with {workers} worker(s) roughly "
              f"~{estimate_seconds(plan) * len(bench.anticheats) / workers / 60:.0f} min plus start-up")
        for trial in trials[: args.show]:
            mods = ", ".join(f"{m['name']}{m['settings']}" for m in trial["modules"]) or "-"
            print(f"  {trial['id']:<32} {trial['arena']:<7} {mods}")


def cmd_run(args) -> None:
    bench = _load(args)
    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    run(bench, run_id, _filter(args.scenarios), artifacts(), args.workers)


def cmd_discover(args) -> None:
    discover(_load(args), artifacts())


def cmd_analyze(args) -> None:
    run_dir = Path(args.run_dir)
    result = analyze_run(run_dir)
    md, page = write_reports(result, run_dir)
    print(f"{md}\n{page}")


def cmd_ci_matrix(args) -> None:
    from . import ci
    jobs = ci.matrix(_load(args), args.run_id, args.stage, artifacts(), _filter(args.scenarios), args.slots,
                     Path(args.tar), install=args.install, discover_missing=args.discover,
                     store=ci.PairStore(Path(args.store)) if args.store else None)
    Path(args.out).write_text(json.dumps(jobs, separators=(",", ":")))


def cmd_ci_shard(args) -> None:
    from . import ci
    bench = _load(args)
    if len(bench.clients) != 1 or len(bench.anticheats) != 1:
        sys.exit("ci shard runs one pair: pass exactly one --clients and one --anticheats")
    sys.exit(0 if ci.shard(bench, args.run_id, artifacts(), args.shard, args.of, Path(args.tar)) else 1)


def cmd_ci_collect(args) -> None:
    from . import ci
    store = ci.PairStore(Path(args.store)) if args.store else None
    sys.exit(0 if ci.collect(Path(args.run_dir), [Path(t) for t in args.tars], store) else 1)


def cmd_serve(args) -> None:
    from .dashboard import serve
    serve(Path(args.results).resolve(), args.host, args.port)


def cmd_export(args) -> None:
    from .dashboard import export
    print(export(Path(args.results).resolve(), Path(args.out).resolve(), args.fragment))


def main() -> None:
    parser = argparse.ArgumentParser(prog="bench", description="Minecraft anticheat benchmark")
    parser.add_argument("--config", default=str(ROOT / "benchmark.toml"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="build driver mod and collector plugin").set_defaults(func=cmd_build)
    for name, func, help_text in (("fetch", cmd_fetch, "download Paper, clients and anticheats"),
                                  ("discover", cmd_discover, "start each client once to record its modules and settings"),
                                  ("plan", cmd_plan, "show the trials that would run"),
                                  ("run", cmd_run, "run the benchmark")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--clients", help="comma separated client ids (default: from benchmark.toml)")
        p.add_argument("--anticheats", help="comma separated anticheat ids, keep 'none' as reference")
        p.add_argument("--scenarios", help="comma separated scenario ids to restrict the run")
        p.add_argument("--reps", type=int, help="override repetitions")
        p.set_defaults(func=func)
        if name == "fetch":
            p.add_argument("--force", action="store_true", help="re-download client and anticheat jars")
        if name == "plan":
            p.add_argument("--show", type=int, default=20, help="number of trials to list")
            p.add_argument("--workers", type=int, help="parallel workers for the time estimate")
        if name == "run":
            p.add_argument("--run-id")
            p.add_argument("--workers", type=int, help="parallel workers (default: [parallel] workers in benchmark.toml)")
    ci = sub.add_parser("ci", help="run one benchmark across many machines (GitHub Actions matrix)")
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)
    for name, func, help_text in (("matrix", cmd_ci_matrix, "write a stage's pair plans and print its shard matrix"),
                                  ("shard", cmd_ci_shard, "run one shard of one client × anticheat pair")):
        p = ci_sub.add_parser(name, help=help_text)
        p.add_argument("--run-id", required=True)
        p.add_argument("--clients", help="comma separated client ids (default: from benchmark.toml)")
        p.add_argument("--anticheats", help="comma separated anticheat ids, keep 'none' as reference")
        p.add_argument("--scenarios", help="comma separated scenario ids to restrict the run")
        p.add_argument("--reps", type=int, help="override repetitions")
        p.add_argument("--tar", required=True, help="tarball to write (plans or the shard folder)")
        p.set_defaults(func=func)
        if name == "matrix":
            p.add_argument("--stage", choices=("reference", "anticheats"), required=True)
            p.add_argument("--slots", type=int, help="parallel machines (default: [parallel] ci_slots)")
            p.add_argument("--out", required=True, help="file for the job matrix (JSON list)")
            p.add_argument("--install", action="store_true", help="also install the game (fills the launcher cache)")
            p.add_argument("--discover", action="store_true", help="discover clients without a module dump first")
            p.add_argument("--store", help="pair store: reuse pairs whose inputs did not change")
        else:
            p.add_argument("--shard", type=int, required=True)
            p.add_argument("--of", type=int, required=True)
    p = ci_sub.add_parser("collect", help="unpack all tarballs of a run, merge shard status and write the reports")
    p.add_argument("run_dir")
    p.add_argument("tars", nargs="+")
    p.add_argument("--store", help="pair store to keep cleanly measured pairs in")
    p.set_defaults(func=cmd_ci_collect)
    p = sub.add_parser("serve", help="live dashboard over all runs in results/")
    p.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to reach it from other machines")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--results", default=str(ROOT / "results"))
    p.set_defaults(func=cmd_serve)
    p = sub.add_parser("export", help="write the dashboard with all runs embedded into one HTML file")
    p.add_argument("--out", default=str(ROOT / "results" / "dashboard.html"))
    p.add_argument("--results", default=str(ROOT / "results"))
    p.add_argument("--fragment", action="store_true", help="omit the html/head/body wrapper (for hosts that add one)")
    p.set_defaults(func=cmd_export)
    p = sub.add_parser("analyze", help="re-analyze a results directory")
    p.add_argument("run_dir")
    p.set_defaults(func=cmd_analyze)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
