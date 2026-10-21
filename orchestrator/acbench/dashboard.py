"""Live dashboard over results/: `./bench serve` shows running and past benchmark runs in the browser."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .analyze import compute_run

PAGE = Path(__file__).with_name("dashboard.html")
RUN_ID = re.compile(r"^[A-Za-z0-9._-]+$")
# A run without live.json (started by an older runner) counts as running while its logs keep changing.
LEGACY_ACTIVE_SECONDS = 120


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def _tail_jsonl(path: Path, max_bytes: int = 256_000) -> list[dict]:
    if not path.exists():
        return []
    with path.open("rb") as f:
        size = path.stat().st_size
        f.seek(max(0, size - max_bytes))
        chunk = f.read().decode("utf-8", errors="replace")
    lines = chunk.splitlines()[1:] if size > max_bytes else chunk.splitlines()
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


class Results:
    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def run_dir(self, run_id: str) -> Path | None:
        if not RUN_ID.match(run_id):
            return None
        path = self.root / run_id
        return path if path.is_dir() else None

    def _latest_mtime(self, run_dir: Path) -> float:
        times = [p.stat().st_mtime for p in run_dir.glob("*/*/*.jsonl")]
        times += [p.stat().st_mtime for p in run_dir.glob("*.json")]
        return max(times, default=0)

    def state(self, run_dir: Path) -> tuple[str, dict | None]:
        live = _read_json(run_dir / "live.json")
        meta = _read_json(run_dir / "run.json") or {}
        if live:
            if live.get("state") == "running" and not _pid_alive(live.get("pid")):
                return "aborted", live
            return live.get("state", "unknown"), live
        # Checked before "finished": a run extended later (e.g. another client) keeps the old finish time meanwhile.
        if time.time() - self._latest_mtime(run_dir) < LEGACY_ACTIVE_SECONDS:
            return "running", None
        if meta.get("finished"):
            return "finished", None
        return "incomplete", None

    def runs(self) -> list[dict]:
        out = []
        for run_dir in self.root.iterdir() if self.root.exists() else []:
            if not run_dir.is_dir():
                continue
            meta = _read_json(run_dir / "run.json") or {}
            state, live = self.state(run_dir)
            results = self.detail_result(run_dir, state) if state == "running" else _read_json(run_dir / "results.json")
            out.append({
                "run_id": run_dir.name,
                "name": meta.get("name"),
                "minecraft": meta.get("minecraft"),
                "started": meta.get("started"),
                "finished": meta.get("finished"),
                "clients": meta.get("clients", []),
                "anticheats": meta.get("anticheats", []),
                "state": state,
                "summaries": (results or {}).get("summaries", []),
                "has_report": (run_dir / "report.html").exists(),
                "sort": meta.get("started") or "",
            })
        # Running runs first, then newest first.
        running = [r for r in out if r["state"] == "running"]
        rest = sorted((r for r in out if r["state"] != "running"), key=lambda r: r["sort"], reverse=True)
        return running + rest

    def detail_result(self, run_dir: Path, state: str) -> dict:
        """Finished runs use their results.json; running ones are re-aggregated when their logs change."""
        if state != "running":
            saved = _read_json(run_dir / "results.json")
            if saved:
                return saved
        mtime = self._latest_mtime(run_dir)
        with self._lock:
            cached = self._cache.get(run_dir.name)
            if cached and cached[0] == mtime:
                return cached[1]
        result, _ = compute_run(run_dir)
        result = json.loads(json.dumps(result, default=str))
        with self._lock:
            self._cache[run_dir.name] = (mtime, result)
        return result

    def detail(self, run_id: str) -> dict | None:
        run_dir = self.run_dir(run_id)
        if run_dir is None:
            return None
        state, live = self.state(run_dir)
        result = self.detail_result(run_dir, state)
        result["state"] = state
        result["has_report"] = (run_dir / "report.html").exists()
        result["live"] = self.live(run_dir, live) if state in ("running", "aborted", "failed") else None
        return result

    def live(self, run_dir: Path, live: dict | None) -> dict:
        pairs = []
        for plan_file in sorted(run_dir.glob("*/*/plan.json")):
            ac_dir = plan_file.parent
            client, anticheat = ac_dir.parent.name, ac_dir.name
            plan = _read_json(plan_file) or {}
            trials = {t["id"]: t for t in plan.get("trials", [])}
            # A sharded run keeps one event log per shard; progress, flags and recent trials are merged across them.
            units = sorted(p.parent for p in ac_dir.glob("shards/*/plan.json")) or [ac_dir]
            completed, currents, flags, recent, last_event = 0, [], [], [], None
            for unit in units:
                completed += len(_read_json(unit / "progress.json") or [])
                events = _tail_jsonl(unit / "server-events.jsonl")
                ended = {e["trial"] for e in events if e.get("type") == "trial_end"}
                begun = [e for e in events if e.get("type") == "trial_begin"]
                if begun and begun[-1]["trial"] not in ended:
                    currents.append(begun[-1]["trial"])
                flags += [e for e in events if e.get("type") == "flag"][-40:]
                recent += [e for e in events if e.get("type") in ("trial_end", "kick")][-12:]
                if events:
                    last_event = max(last_event or 0, events[-1].get("time_ms") or 0)
            flags = sorted(flags, key=lambda e: e.get("time_ms") or 0)[-40:]
            recent = sorted(recent, key=lambda e: e.get("time_ms") or 0)[-12:]
            info = lambda trial_id: trials.get(trial_id) and {
                k: trials[trial_id][k] for k in ("scenario", "variant", "phase", "rep", "category")}
            entry = {
                "client": client, "anticheat": anticheat, "total": len(trials), "completed": completed,
                "current": currents[0] if currents else None,
                "current_info": info(currents[0]) if currents else None,
                "current_all": [info(c) for c in currents if info(c)],
                "flags": [{k: f.get(k) for k in ("time_ms", "tick", "check", "vl", "player")} for f in flags],
                "recent": [{
                    "type": e["type"], "trial": e.get("trial"), "time_ms": e.get("time_ms"),
                    "metric": trials.get(e.get("trial"), {}).get("metric"),
                    "value": (e.get("metrics") or {}).get(trials.get(e.get("trial"), {}).get("metric")),
                    "reason": e.get("reason"),
                } for e in recent],
                "last_event_ms": last_event,
            }
            if live:
                status = next((p for p in live.get("pairs", []) if p["client"] == client and p["anticheat"] == anticheat), None)
                entry["status"] = status
            pairs.append(entry)
        if live:
            known = {(p["client"], p["anticheat"]) for p in pairs}
            pairs += [{"client": p["client"], "anticheat": p["anticheat"], "total": p.get("trials"), "completed": 0,
                       "status": p, "flags": [], "recent": []}
                      for p in live.get("pairs", []) if (p["client"], p["anticheat"]) not in known]
        return {"status": live, "pairs": pairs, "now_ms": int(time.time() * 1000)}


def make_handler(results: Results):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: int = HTTPStatus.OK) -> None:
            self._send(status, json.dumps(data, default=str).encode(), "application/json; charset=utf-8")

        def do_GET(self):
            path = self.path.split("?", 1)[0].rstrip("/") or "/"
            try:
                if path == "/":
                    self._send(HTTPStatus.OK, PAGE.read_bytes(), "text/html; charset=utf-8")
                elif path == "/api/runs":
                    self._json(results.runs())
                elif m := re.fullmatch(r"/api/runs/([^/]+)", path):
                    detail = results.detail(m.group(1))
                    self._json(detail) if detail else self._json({"error": "unknown run"}, HTTPStatus.NOT_FOUND)
                elif m := re.fullmatch(r"/runs/([^/]+)/report", path):
                    run_dir = results.run_dir(m.group(1))
                    report = run_dir / "report.html" if run_dir else None
                    if report and report.exists():
                        self._send(HTTPStatus.OK, report.read_bytes(), "text/html; charset=utf-8")
                    else:
                        self._json({"error": "no report"}, HTTPStatus.NOT_FOUND)
                else:
                    self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except BrokenPipeError:
                pass
            except Exception as error:  # surfaced in the UI instead of killing the server
                self._json({"error": f"{type(error).__name__}: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    return Handler


def export(results_dir: Path, out: Path, fragment: bool = False) -> Path:
    """Writes the dashboard as one self-contained file with every run embedded (no server needed).

    fragment=True leaves out the doctype/html/head/body wrapper, for hosts that add their own (claude.ai artifacts).
    """
    results = Results(results_dir)
    runs = results.runs()
    details = {}
    for run in runs:
        detail = results.detail(run["run_id"])
        if detail:
            detail["has_report"] = False  # the static report is not part of the snapshot
            details[run["run_id"]] = detail
    snapshot = {"created_ms": int(time.time() * 1000), "runs": runs, "details": details}
    data = json.dumps(snapshot, default=str).replace("</", "<\\/")
    page = PAGE.read_text().replace("<!--SNAPSHOT-->", f"<script>window.ACBENCH_SNAPSHOT = {data};</script>", 1)
    if fragment:
        head = page[page.index("<head>") + 6:page.index("</head>")]
        head = re.sub(r'<meta (charset|name="viewport")[^>]*>\s*', "", head)
        body = page[page.index("<body>") + 6:page.index("</body>")]
        page = head.strip() + "\n" + body.strip() + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def serve(results_dir: Path, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(Results(results_dir)))
    print(f"[serve] dashboard on http://{host}:{port}  (results: {results_dir})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
