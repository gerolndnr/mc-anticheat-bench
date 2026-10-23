"""Runs the benchmark matrix on a pool of workers.

Every client × anticheat run is split into shards: disjoint sets of trials, each driven by its own server, bot
and target bot on its own port. Trials are independent (the bot rejoins before each one), so shards can run side by
side on several workers. The reference runs ("none") are scheduled first because the anticheat runs of a client only
repeat the variants that showed an effect there; as soon as a client's reference is complete its anticheat shards
start, while other clients may still be measuring their reference.
"""
from __future__ import annotations

import json
import math
import os
import queue
import shutil
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from . import fetch
from .analyze import REFERENCE_AC, analyze_run, compute_run
from .config import AntiCheat, Benchmark, Client as ClientConfig
from .plan import build_plan, build_trials, estimate_seconds, module_dump_file
from .processes import Client, Server
from .report import write_reports

# Starting servers and clients one at a time avoids races on first-run patching (Paperclip) and on Xvfb display
# numbers, and keeps start-up CPU spikes away from shards that are already measuring.
_START_LOCK = threading.Lock()
_START_SPACING_SECONDS = 3


def _events_done(events_file: Path) -> bool:
    if not events_file.exists():
        return False
    with events_file.open("rb") as f:
        f.seek(max(0, events_file.stat().st_size - 4096))
        return b'"type":"done"' in f.read()


def _joined(events_file: Path, player: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    needle = '"type":"join"'
    while time.time() < deadline:
        if events_file.exists() and any(needle in line and f'"player":"{player}"' in line
                                        for line in events_file.read_text().splitlines()):
            return True
        time.sleep(2)
    return False


def _screen(run_dir: Path, client_id: str, ac_id: str, trials: list[dict]) -> list[dict]:
    """Drops cheat variants that gave no advantage in the reference run, except those named after this anticheat
    (targeted bypasses can only work with it). Baselines always stay."""
    result, _ = compute_run(run_dir)
    reference = {(v["scenario"], v["variant"]): v for v in result["variants"]
                 if v["client"] == client_id and v["anticheat"] == REFERENCE_AC}
    if not reference:
        return trials
    kept = [t for t in trials if t["phase"] == "baseline" or ac_id.lower() in t["variant"].lower()
            or (t["scenario"], t["variant"]) not in reference or reference[(t["scenario"], t["variant"])]["effective"]]
    dropped = {(t["scenario"], t["variant"]) for t in trials} - {(t["scenario"], t["variant"]) for t in kept}
    if dropped:
        print(f"[run] {client_id} vs {ac_id}: skipping {len(dropped)} variants without effect in the reference run")
    return kept


def _needs_target_player(trials: list[dict]) -> bool:
    return any(t.get("type") == "player" for trial in trials for t in trial.get("targets", []))


def _count(events_file: Path, *needles: str) -> int:
    if not events_file.exists():
        return 0
    return sum(1 for line in events_file.read_text().splitlines() if all(n in line for n in needles))


def _wait_count(events_file: Path, before: int, timeout: float, *needles: str) -> bool:
    """Waits until more lines than `before` contain all needles (e.g. a new server_ready after a restart)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _count(events_file, *needles) > before:
            return True
        time.sleep(1)
    return False


def _last_disconnected_trial(client_log: Path) -> str | None:
    """Trial the driver gave up on when it lost the connection (it marks it as done so it cannot loop forever)."""
    if not client_log.exists():
        return None
    for line in reversed(client_log.read_text().splitlines()):
        if '"type":"disconnected"' in line:
            try:
                return json.loads(line).get("trial") or None
            except ValueError:
                return None
    return None


def _unskip(progress_file: Path, trial_id: str) -> bool:
    try:
        done = json.loads(progress_file.read_text())
    except (OSError, ValueError):
        return False
    if trial_id not in done:
        return False
    progress_file.write_text(json.dumps([t for t in done if t != trial_id]))
    return True


def _progress(progress_file: Path) -> int:
    try:
        return len(json.loads(progress_file.read_text()))
    except (OSError, ValueError):
        return 0


def _server_ready(events_file: Path, timeout: float = 60) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if events_file.exists():
            for line in events_file.read_text().splitlines():
                if '"type":"server_ready"' in line:
                    return json.loads(line)
        time.sleep(1)
    return None


def resolve_workers(bench: Benchmark, override: int | None = None) -> int:
    """Worker count from --workers, [parallel] workers, or "auto": one worker per ~3 cores and ~7 GB of memory,
    which is what a server, a software-rendered client and the target bot need without slowing each other down."""
    value = override if override is not None else bench.parallel.get("workers", "auto")
    if value != "auto":
        return max(1, int(value))
    cores = os.cpu_count() or 2
    try:
        memory_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except (ValueError, OSError):
        memory_gb = 8
    return max(1, min(cores // 3, int(memory_gb // 7)))


class LiveStatus:
    """results/<run>/live.json: what the runner is doing right now, read by the dashboard (./bench serve).
    Shared by all worker threads."""

    def __init__(self, run_dir: Path, run_id: str, pairs: list[tuple[str, str]], workers: int):
        self.file = run_dir / "live.json"
        self.lock = threading.Lock()
        self.data = {
            "run_id": run_id, "state": "running", "pid": os.getpid(), "started": time.time(), "updated": time.time(),
            "current": None, "phase": "preparing", "workers": workers,
            "pairs": [{"client": c, "anticheat": a, "status": "pending", "shards": []} for c, a in pairs],
        }
        self.write()

    def update(self, **fields) -> None:
        with self.lock:
            self.data.update(fields)
            self._write()

    def pair(self, client: str, anticheat: str, **fields) -> None:
        with self.lock:
            self._pair(client, anticheat).update(fields)
            self._write()

    def pair_started(self, client: str, anticheat: str, shards: int, approx_trials: int) -> None:
        """Called by every shard; only the first one sets the start time used for the remaining-time estimate."""
        with self.lock:
            entry = self._pair(client, anticheat)
            entry.setdefault("pair_started", time.time())
            entry.update(shard_count=shards, trials=entry.get("trials") or approx_trials)
            self._write()

    def shard(self, client: str, anticheat: str, shard: int, status: str, **fields) -> None:
        with self.lock:
            entry = self._pair(client, anticheat)
            shards = {s["shard"]: s for s in entry["shards"]}
            shards.setdefault(shard, {"shard": shard}).update(status=status, **fields)
            entry["shards"] = [shards[k] for k in sorted(shards)]
            states = [s["status"] for s in entry["shards"]]
            # The pair reads as running while any shard runs, and as done or failed once all of them stopped.
            entry["status"] = ("running" if "running" in states else "starting server" if "starting server" in states
                               else "error" if "error" in states and all(s in ("done", "error") for s in states)
                               else "done" if all(s == "done" for s in states) else "pending")
            entry["restarts"] = sum(s.get("restarts", 0) for s in entry["shards"])
            errors = [s["error"] for s in entry["shards"] if s.get("error")]
            entry["error"] = "; ".join(errors) if errors else None
            self.data["current"] = {"client": client, "anticheat": anticheat}
            self.data["phase"] = "running"
            self._write()

    def _pair(self, client: str, anticheat: str) -> dict:
        for entry in self.data["pairs"]:
            if entry["client"] == client and entry["anticheat"] == anticheat:
                return entry
        entry = {"client": client, "anticheat": anticheat, "status": "pending", "shards": []}
        self.data["pairs"].append(entry)
        return entry

    def write(self) -> None:
        with self.lock:
            self._write()

    def _write(self) -> None:
        self.data["updated"] = time.time()
        tmp = self.file.with_suffix(f".{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(self.data, indent=1))
        tmp.replace(self.file)


@dataclass
class Job:
    client: ClientConfig
    ac: AntiCheat
    shard: int
    shards: int
    unit_dir: Path
    trials: list[dict]


class Runner:
    def __init__(self, bench: Benchmark, run_id: str, scenario_filter: set[str] | None, artifacts: dict[str, Path],
                 workers: int):
        self.bench = bench
        self.run_id = run_id
        self.scenario_filter = scenario_filter
        self.artifacts = artifacts
        self.workers = workers
        self.root = bench.root
        self.cache, self.work = self.root / "cache", self.root / "work"
        self.run_dir = self.root / "results" / run_id
        self.meta_lock = threading.Lock()
        self.slots: queue.Queue[int] = queue.Queue()
        for slot in range(workers):
            self.slots.put(slot)

    # ---- setup -------------------------------------------------------------------------------------------------
    def prepare(self, install: bool = True) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        previous = self.run_dir / "run.json"
        old = json.loads(previous.read_text()) if previous.exists() else {}
        # Jars an earlier invocation of this run recorded are reused as they are, so every shard of a run measures
        # the same builds even when they run on different machines and a newer release appeared in between.
        pinned_paths = old.get("jar_paths", {})

        def pinned(key: str, fetcher) -> list[Path]:
            paths = [self.root / p for p in pinned_paths.get(key, [])]
            return paths if paths and all(p.exists() for p in paths) else fetcher()

        self.paper_jar = pinned("paper", lambda: [fetch.paper(self.bench, self.cache)])[0]
        bench = self.bench
        meta = {
            "name": bench.name, "run_id": self.run_id, "minecraft": bench.minecraft, "repetitions": bench.repetitions,
            "grace_ticks": bench.grace_ticks, "scoring": bench.scoring, "clients": bench.client_ids,
            "anticheats": bench.anticheat_ids, "paper": self.paper_jar.name,
            "target_player": bench.client.get("target_username", "BenchTarget"),
            "started": time.strftime("%Y-%m-%d %H:%M:%S"), "workers": self.workers, "jars": {}, "jar_paths": {},
            "status": {},
        }
        if old:
            # Re-running parts of a run (e.g. a single anticheat) keeps what earlier invocations recorded.
            meta["jars"] = old.get("jars", {})
            meta["jar_paths"] = dict(pinned_paths)
            meta["status"] = old.get("status", {})
            meta["anticheats"] = sorted(set(old.get("anticheats", [])) | set(bench.anticheat_ids), key=lambda a: (a != "none", a))
            meta["clients"] = sorted(set(old.get("clients", [])) | set(bench.client_ids))
            meta["started"] = old.get("started", meta["started"])
        self.meta = meta

        def record(key: str, jars: list[Path]) -> list[Path]:
            meta["jars"][key] = [j.name for j in jars]
            meta["jar_paths"][key] = [os.path.relpath(j, self.root) for j in jars]
            return jars

        # Downloads and builds happen once, before any worker starts.
        record("paper", [self.paper_jar])
        self.client_jars = {}
        for client in bench.clients.values():
            key = f"client:{client.id}"
            self.client_jars[client.id] = record(key, pinned(key, lambda: fetch.client_mod(bench, client, self.cache)))
        self.ac_jars = {}
        for ac in bench.anticheats.values():
            key = f"anticheat:{ac.id}"
            self.ac_jars[ac.id] = record(key, pinned(key, lambda: fetch.anticheat(bench, ac, self.cache)))
        self.save_meta()
        if not install:
            return
        # The game itself is installed once; parallel launchers then only read the shared folder.
        installer = Client(bench, self.work / "clients" / "_install", self.work / "launcher", [], self.run_dir / "run.json",
                           self.run_dir / "install.log")
        installer.game_dir.mkdir(parents=True, exist_ok=True)
        installer.install()

    def save_meta(self) -> None:
        with self.meta_lock:
            (self.run_dir / "run.json").write_text(json.dumps(self.meta, indent=2))

    # ---- planning ----------------------------------------------------------------------------------------------
    def write_pair(self, client: ClientConfig, ac: AntiCheat, trials: list[dict]) -> Path:
        """Writes the pair's full plan, which the analysis and every shard of the pair read."""
        out = self.run_dir / client.id / ac.id
        out.mkdir(parents=True, exist_ok=True)
        (out / "anticheat.json").write_text(json.dumps({
            "id": ac.id, "name": ac.name, "default_alerts": ac.default_alerts,
            "default_alert_aliases": ac.default_alert_aliases, "known_issues": ac.known_issues,
        }, indent=1))
        full_plan = build_plan(self.bench, client, self.run_id, trials, {
            "progress": str((out / "progress.json").resolve()),
            "client_log": str((out / "client-events.jsonl").resolve()),
            "modules_dump": str((out / "modules.json").resolve()),
        })
        (out / "plan.json").write_text(json.dumps(full_plan, indent=1))
        return out

    def make_jobs(self, client: ClientConfig, ac: AntiCheat, trials: list[dict]) -> list[Job]:
        """Writes the pair's full plan and splits its trials round-robin into shards (a mix of scenarios each)."""
        out = self.run_dir / client.id / ac.id
        legacy = (out / "server-events.jsonl").exists() and not (out / "shards").exists()
        self.write_pair(client, ac, trials)
        if legacy:
            # A run started before sharding existed is resumed in its original single-server layout.
            return [Job(client, ac, 0, 1, out, trials)]
        existing = sorted((out / "shards").glob("s*")) if (out / "shards").exists() else []
        min_trials = int(self.bench.parallel.get("min_trials_per_shard", 30))
        # A resumed run keeps its shard layout, so every trial stays with the progress file that knows about it.
        shards = len(existing) or max(1, min(self.workers, math.ceil(len(trials) / min_trials)))
        return [Job(client, ac, k, shards, out / "shards" / f"s{k}", trials[k::shards]) for k in range(shards)]

    # ---- scheduling --------------------------------------------------------------------------------------------
    def run_all(self, live: LiveStatus) -> None:
        bench = self.bench
        reference = bench.anticheats.get(REFERENCE_AC)
        others = [ac for ac in bench.anticheats.values() if ac.id != REFERENCE_AC]
        all_trials = {c.id: build_trials(bench, c, self.scenario_filter) for c in bench.clients.values()}
        pending_reference: dict[str, int] = {}
        futures = {}

        with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="worker") as pool:
            def submit(job: Job) -> None:
                futures[pool.submit(self.run_job, job, live)] = job

            def submit_anticheats(client: ClientConfig) -> None:
                for ac in others:
                    trials = all_trials[client.id]
                    if reference and bench.timing.get("screen_variants", True):
                        trials = _screen(self.run_dir, client.id, ac.id, trials)
                    for job in self.make_jobs(client, ac, trials):
                        submit(job)

            # Reference shards of every client go first; they decide which variants the anticheat runs repeat.
            for client in bench.clients.values():
                if reference:
                    jobs = self.make_jobs(client, reference, all_trials[client.id])
                    pending_reference[client.id] = len(jobs)
                    for job in jobs:
                        submit(job)
                else:
                    submit_anticheats(client)

            while futures:
                done, _ = wait(list(futures), return_when=FIRST_COMPLETED)
                for future in done:
                    job = futures.pop(future)
                    if future.exception():
                        print(f"[run] {job.client.id}/{job.ac.id}#{job.shard}: failed – {future.exception()!r}")
                    if job.ac.id == REFERENCE_AC:
                        pending_reference[job.client.id] -= 1
                        if pending_reference[job.client.id] == 0:
                            submit_anticheats(job.client)

    def run_job(self, job: Job, live: LiveStatus) -> None:
        slot = self.slots.get()
        try:
            self.run_shard(job, slot, live)
        finally:
            self.slots.put(slot)

    # ---- one shard on one worker -------------------------------------------------------------------------------
    def run_shard(self, job: Job, slot: int, live: LiveStatus) -> dict:
        bench, client, ac, out = self.bench, job.client, job.ac, job.unit_dir
        tag = f"{client.id}/{ac.id}" + (f"#{job.shard}" if job.shards > 1 else "")
        out.mkdir(parents=True, exist_ok=True)
        port = int(bench.server.get("port", 25599)) + slot
        plan = build_plan(bench, client, self.run_id, job.trials, {
            "progress": str((out / "progress.json").resolve()),
            "client_log": str((out / "client-events.jsonl").resolve()),
            "modules_dump": str((out / "modules.json").resolve()),
        })
        plan["server_address"] = f"127.0.0.1:{port}"
        plan_file = out / "plan.json"
        plan_file.write_text(json.dumps(plan, indent=1))
        estimate = estimate_seconds(plan)
        print(f"[run] {tag}: {len(job.trials)} trials on worker {slot} (port {port}), ~{estimate / 60:.0f} min")
        live.pair_started(client.id, ac.id, job.shards, len(job.trials) * job.shards)
        live.shard(client.id, ac.id, job.shard, "starting server", slot=slot, trials=len(job.trials),
                   estimate_seconds=estimate, started=time.time())

        events = out / "server-events.jsonl"
        server = Server(bench, self.work / "servers" / f"w{slot}", self.paper_jar, self.artifacts["collector"], ac,
                        self.ac_jars[ac.id], plan_file, events, out / "server.log", port=port)
        game = Client(bench, self.work / "clients" / client.id / f"w{slot}", self.work / "launcher",
                      self.client_jars[client.id] + [self.artifacts["driver"]], plan_file, out / "client.log",
                      client.jvm_args, port=port)
        target = None
        if _needs_target_player(job.trials):
            target_plan = out / "target-plan.json"
            target_plan.write_text(json.dumps({
                "run_id": self.run_id, "role": "dummy", "client": {"id": "target", "adapter": "none"},
                "client_log": str((out / "target-events.jsonl").resolve()),
            }))
            target = Client(bench, self.work / "clients" / "_target" / f"w{slot}", self.work / "launcher",
                            [self.artifacts["driver"]], target_plan, out / "target.log",
                            username=bench.client.get("target_username", "BenchTarget"),
                            memory=bench.client.get("target_memory", "1500M"),
                            options={"maxFps": "10", "renderDistance": "2", "simulationDistance": "5"}, port=port)
        status = {"restarts": 0, "finished": False, "worker": slot}
        stalled_restarts, last_progress = 0, _progress(out / "progress.json")
        server.prepare(self.work / "paper-shared")
        try:
            with _START_LOCK:
                server.start()
            # A broken anticheat build must not silently produce a run with zero detections.
            ready = _server_ready(events)
            enabled = {p["name"]: p["enabled"] for p in (ready or {}).get("plugins", [])}
            if ready is None or (ac.plugin and not enabled.get(ac.plugin)):
                status["error"] = f"anticheat plugin {ac.plugin!r} is not enabled, see {out / 'server.log'}"
                raise RuntimeError(status["error"])
            if target:
                # The player target has to stand on the server before the first combat trial.
                target.prepare()
                self._start(target)
                if not _joined(events, target.username, 300):
                    status["error"] = "target bot did not join"
                    raise RuntimeError(status["error"])
            live.shard(client.id, ac.id, job.shard, "running")
            game.prepare()
            self._start(game)
            # The limit only guards against a stuck client, so it grows with the plan.
            deadline = time.time() + max(float(bench.client.get("timeout_seconds", 3600)), 2 * estimate + 600)
            # A client that is alive but makes no progress (e.g. locked out of the server and sitting on the
            # disconnect screen) is restarted like one that exited, so it cannot hold the shard until the deadline.
            stall_seconds = float(bench.client.get("stall_seconds", 300))
            seen_progress, progress_at = last_progress, time.time()
            outside_kicks, server_restarts, retried = _count(events, '"type":"kick"', '"trial":""'), 0, set()
            max_server_restarts = int(bench.client.get("max_server_restarts", 3))
            while not _events_done(events):
                if time.time() > deadline:
                    status["error"] = "timeout"
                    break
                progress = _progress(out / "progress.json")
                if progress != seen_progress:
                    seen_progress, progress_at = progress, time.time()
                elif game.running() and time.time() - progress_at > stall_seconds:
                    print(f"[run] {tag}: no trial completed for {stall_seconds:.0f} s, stopping the client")
                    status["stalls"] = status.get("stalls", 0) + 1
                    game.stop()
                    progress_at = time.time()
                if target and not target.running():
                    print(f"[run] {tag}: target bot exited, restarting it")
                    self._start(target)
                if not game.running():
                    # A kick while no trial runs cannot come from a cheat: the server, typically the anticheat's
                    # per-player state, is broken. Rejoining the same server would be kicked again (each time
                    # skipping a trial), so the server is restarted fresh and the lost trial gets one more try.
                    kicks = _count(events, '"type":"kick"', '"trial":""')
                    if kicks > outside_kicks and server_restarts < max_server_restarts:
                        outside_kicks, server_restarts = kicks, server_restarts + 1
                        lost = _last_disconnected_trial(out / "client-events.jsonl")
                        if lost and lost not in retried and _unskip(out / "progress.json", lost):
                            retried.add(lost)
                        print(f"[run] {tag}: kicked outside a trial, restarting the server ({server_restarts}/"
                              f"{max_server_restarts}){f', retrying {lost}' if lost in retried else ''}")
                        status["server_restarts"] = server_restarts
                        if target:
                            target.stop()
                        server.stop()
                        ready_before = _count(events, '"type":"server_ready"')
                        server.prepare(self.work / "paper-shared")
                        with _START_LOCK:
                            server.start()
                        if not _wait_count(events, ready_before, 120, '"type":"server_ready"'):
                            status["error"] = "server did not come back after a restart"
                            break
                        if target:
                            joins_before = _count(events, '"type":"join"', f'"player":"{target.username}"')
                            self._start(target)
                            _wait_count(events, joins_before, 300, '"type":"join"', f'"player":"{target.username}"')
                        last_progress = _progress(out / "progress.json")
                    # Only restarts without any completed trial in between count towards the limit.
                    progress = _progress(out / "progress.json")
                    stalled_restarts = 0 if progress > last_progress else stalled_restarts + 1
                    last_progress = progress
                    if stalled_restarts > int(bench.client.get("max_restarts", 3)):
                        status["error"] = "client kept stopping without progress"
                        break
                    status["restarts"] += 1
                    print(f"[run] {tag}: client stopped early, restart {status['restarts']} (progress is kept)")
                    live.shard(client.id, ac.id, job.shard, "running", restarts=status["restarts"])
                    time.sleep(5)
                    self._start(game)
                time.sleep(2)
            status["finished"] = _events_done(events)
            # Give the driver a moment to quit on its own after "done".
            for _ in range(30):
                if not game.running():
                    break
                time.sleep(1)
        except RuntimeError as error:
            print(f"[run] {tag}: skipped – {error}")
        finally:
            game.stop()
            if target:
                target.stop()
            server.stop()
        with self.meta_lock:
            self.meta["status"].setdefault(f"{client.id}/{ac.id}", {})[f"s{job.shard}"] = status
        self.save_meta()
        # Shards run on other machines (CI) bring their status along in their own folder.
        (out / "status.json").write_text(json.dumps(status, indent=1))
        print(f"[run] {tag}: {status}")
        live.shard(client.id, ac.id, job.shard, "done" if status["finished"] else "error", error=status.get("error"),
                   restarts=status["restarts"])
        if (out / "modules.json").exists():
            fetch.copy(out / "modules.json", module_dump_file(bench, client))
        return status

    @staticmethod
    def _start(process: Client) -> None:
        with _START_LOCK:
            process.start()
            time.sleep(_START_SPACING_SECONDS)


def discover(bench: Benchmark, artifacts: dict[str, Path]) -> None:
    """Starts each client once without trials so it writes its module dump (needed for generated variants)."""
    bench.anticheats = {k: v for k, v in bench.anticheats.items() if k == REFERENCE_AC}
    bench.anticheat_ids = [REFERENCE_AC]
    run_id = f"discover-{time.strftime('%Y%m%d-%H%M%S')}"
    run_dir = run(bench, run_id, {"__no_scenario__"}, artifacts)
    for client in bench.clients.values():
        dump = module_dump_file(bench, client)
        print(f"[discover] {client.id}: {'module dump at ' + str(dump) if dump.exists() else 'no module dump written, see ' + str(run_dir)}")
    if all(module_dump_file(bench, c).exists() for c in bench.clients.values()):
        shutil.rmtree(run_dir)


def run(bench: Benchmark, run_id: str, scenario_filter: set[str] | None, artifacts: dict[str, Path],
        workers: int | None = None) -> Path:
    runner = Runner(bench, run_id, scenario_filter, artifacts, resolve_workers(bench, workers))
    runner.prepare()
    print(f"[run] {run_id}: {runner.workers} worker(s)")
    live = LiveStatus(runner.run_dir, run_id, [(c, a) for c in bench.clients for a in bench.anticheats], runner.workers)
    try:
        runner.run_all(live)
        live.update(phase="analyzing", current=None)
        runner.meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        runner.save_meta()
        result = analyze_run(runner.run_dir)
        md, page = write_reports(result, runner.run_dir)
        print(f"[run] report: {md} / {page}")
        live.update(state="finished", phase="finished")
    except BaseException as error:
        live.update(state="failed", phase="failed", error=f"{type(error).__name__}: {error}")
        raise
    return runner.run_dir
