"""Starts and stops the Paper server and the Minecraft client for one benchmark run."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .config import AntiCheat, Benchmark
from .fetch import copy

SERVER_PROPERTIES = {
    "online-mode": "false",
    "white-list": "false",
    "enforce-whitelist": "false",
    "enforce-secure-profile": "false",
    "level-type": "minecraft\\:flat",
    "generate-structures": "false",
    "spawn-protection": "0",
    "difficulty": "easy",
    "gamemode": "survival",
    "pvp": "true",
    "max-players": "4",
    "view-distance": "6",
    "simulation-distance": "6",
    "sync-chunk-writes": "false",
    "motd": "acbench",
    "level-seed": "acbench",
}

# Shared between runs so Paperclip does not re-download and re-patch the vanilla server every time.
PAPER_SHARED_DIRS = ("cache", "libraries", "versions")

CLIENT_OPTIONS = {
    "pauseOnLostFocus": "false",
    "onboardAccessibility": "false",
    "skipMultiplayerWarning": "true",
    "joinedFirstServer": "true",
    "tutorialStep": "none",
    "renderDistance": "4",
    "simulationDistance": "5",
    "maxFps": "30",
    "soundCategory_master": "0.0",
    "narrator": "0",
}


class LogTail:
    """Copies a process's stdout to a file and remembers whether a marker line has appeared."""

    def __init__(self, process: subprocess.Popen, log_file: Path, marker: str | None = None):
        self.marker = marker
        self.seen = threading.Event()
        self._thread = threading.Thread(target=self._pump, args=(process, log_file), daemon=True)
        self._thread.start()

    def _pump(self, process: subprocess.Popen, log_file: Path) -> None:
        with log_file.open("a", encoding="utf-8", errors="replace") as out:
            for line in iter(process.stdout.readline, ""):
                out.write(line)
                out.flush()
                if self.marker and self.marker in line:
                    self.seen.set()


class Server:
    def __init__(self, bench: Benchmark, workdir: Path, paper_jar: Path, collector_jar: Path,
                 ac: AntiCheat, ac_jars: list[Path], plan_file: Path, events_file: Path, log_file: Path,
                 port: int | None = None):
        self.bench = bench
        self.port = port or int(bench.server.get("port", 25599))
        self.dir = workdir
        self.paper_jar = paper_jar
        self.collector_jar = collector_jar
        self.ac = ac
        self.ac_jars = ac_jars
        self.plan_file = plan_file
        self.events_file = events_file
        self.log_file = log_file
        self.process: subprocess.Popen | None = None

    def prepare(self, shared: Path) -> None:
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True)
        for name in PAPER_SHARED_DIRS:
            (shared / name).mkdir(parents=True, exist_ok=True)
            (self.dir / name).symlink_to((shared / name).resolve(), target_is_directory=True)
        (self.dir / "eula.txt").write_text("eula=true\n")

        props = dict(SERVER_PROPERTIES)
        props["server-port"] = str(self.port)
        # Vanilla kicks for "flying" independently of the movement-check gamerule.
        props["allow-flight"] = "false" if self.bench.server.get("vanilla_movement_checks") else "true"
        props.update({k: str(v) for k, v in self.bench.server.get("properties", {}).items()})
        (self.dir / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in props.items()))

        plugins = self.dir / "plugins"
        copy(self.collector_jar, plugins / self.collector_jar.name)
        for jar in self.ac_jars:
            copy(jar, plugins / jar.name)
        (plugins / "bStats").mkdir(parents=True)
        (plugins / "bStats" / "config.yml").write_text("enabled: false\n")
        collector_cfg = {
            "plan_file": str(self.plan_file.resolve()),
            "output_file": str(self.events_file.resolve()),
            "anticheat": self.ac.id,
            "vanilla_movement_checks": bool(self.bench.server.get("vanilla_movement_checks", False)),
            "target_player": self.bench.client.get("target_username", "BenchTarget"),
            "target_permissions": self.ac.target_bypass_permissions,
            "flag_sources": self.ac.flag_sources,
        }
        (plugins / "AcBenchCollector").mkdir(parents=True)
        # JSON is valid YAML, so Bukkit reads this as its config.yml.
        (plugins / "AcBenchCollector" / "config.yml").write_text(json.dumps(collector_cfg, indent=2))
        for target, source in self.ac.files.items():
            copy(source, self.dir / target)

    def start(self, timeout: float = 300) -> None:
        java = self.bench.server.get("java") or os.environ.get("ACBENCH_JAVA", "java")
        cmd = [java, f"-Xmx{self.bench.server.get('memory', '2G')}", "-jar", str(self.paper_jar.resolve()), "--nogui"]
        self.process = subprocess.Popen(cmd, cwd=self.dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, bufsize=1)
        tail = LogTail(self.process, self.log_file, marker="Done (")
        deadline = time.time() + timeout
        while not tail.seen.wait(1):
            if self.process.poll() is not None:
                raise RuntimeError(f"Server exited during startup, see {self.log_file}")
            if time.time() > deadline:
                self.stop()
                raise TimeoutError(f"Server did not start within {timeout}s, see {self.log_file}")

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        try:
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            self.process.wait(90)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()
            self.process.wait()


class Client:
    def __init__(self, bench: Benchmark, game_dir: Path, launcher_dir: Path, mod_jars: list[Path],
                 plan_file: Path, log_file: Path, jvm_args: list[str] | None = None,
                 username: str | None = None, memory: str | None = None, options: dict[str, str] | None = None,
                 port: int | None = None):
        self.bench = bench
        self.port = port or int(bench.server.get("port", 25599))
        self.jvm_args = jvm_args or []
        self.username = username or bench.client.get("username", "BenchBot")
        self.memory = memory or bench.client.get("memory", "3G")
        self.options = options or {}
        self.game_dir = game_dir
        self.launcher_dir = launcher_dir
        self.mod_jars = mod_jars
        self.plan_file = plan_file
        self.log_file = log_file
        self.process: subprocess.Popen | None = None

    def prepare(self) -> None:
        mods = self.game_dir / "mods"
        if mods.exists():
            shutil.rmtree(mods)
        mods.mkdir(parents=True)
        for jar in self.mod_jars:
            copy(jar, mods / jar.name)
        options = self.game_dir / "options.txt"
        existing = {}
        if options.exists():
            for line in options.read_text().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    existing[key] = value
        existing.update(CLIENT_OPTIONS)
        existing.update(self.options)
        options.write_text("".join(f"{k}:{v}\n" for k, v in existing.items()))

    def command(self) -> list[str]:
        cfg = self.bench.client
        version = f"fabric:{self.bench.minecraft}:{cfg.get('fabric_loader', '')}".rstrip(":")
        cmd = [
            cfg.get("launcher", "portablemc"), "--main-dir", str(self.launcher_dir.resolve()),
            "start", version,
            "--mc-dir", str(self.game_dir.resolve()),
            "-u", self.username,
            "--join-server", "127.0.0.1",
            "--join-server-port", str(self.port),
            f"--jvm-arg=-Xmx{self.memory}",
            f"--jvm-arg=-Dacbench.plan={self.plan_file.resolve()}",
        ] + [f"--jvm-arg={arg}" for arg in self.jvm_args]
        if cfg.get("java"):
            cmd += ["--jvm", cfg["java"]]
        if cfg.get("headless", True):
            cmd = ["xvfb-run", "-a", "-s", "-screen 0 1280x720x24"] + cmd
        return cmd

    def install(self) -> None:
        """Installs the game version and loader once, so parallel workers never download into the same folder."""
        cfg = self.bench.client
        version = f"fabric:{self.bench.minecraft}:{cfg.get('fabric_loader', '')}".rstrip(":")
        cmd = [cfg.get("launcher", "portablemc"), "--main-dir", str(self.launcher_dir.resolve()), "start", version,
               "--mc-dir", str(self.game_dir.resolve()), "--dry"]
        if cfg.get("java"):
            cmd += ["--jvm", cfg["java"]]
        with self.log_file.open("a") as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)

    def start(self) -> None:
        env = dict(os.environ)
        if self.bench.client.get("headless", True):
            env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
            # Xvfb offers no sRGB GLX visual; EGL lets the OpenGL backend start instead of falling back to Vulkan.
            env.setdefault("SDL_VIDEO_FORCE_EGL", "1")
        with self.log_file.open("a") as log:
            log.write(f"\n=== client start {time.strftime('%H:%M:%S')}: {' '.join(self.command())}\n")
        self.process = subprocess.Popen(self.command(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, bufsize=1, env=env, start_new_session=True)
        LogTail(self.process, self.log_file)

    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self) -> None:
        if not self.running():
            return
        try:
            os.killpg(self.process.pid, 15)
            self.process.wait(30)
        except (OSError, subprocess.TimeoutExpired):
            os.killpg(self.process.pid, 9)
            self.process.wait()
