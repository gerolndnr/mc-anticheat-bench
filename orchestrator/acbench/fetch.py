"""Downloads server, client and anticheat jars into cache/, reusing what is already there."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from .config import AntiCheat, Benchmark, Client

USER_AGENT = "acbench/0.1 (anticheat benchmark)"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _download(url: str, target: Path, force: bool = False) -> Path:
    if target.exists() and not force:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"[fetch] {url} -> {target}")
    tmp = target.with_suffix(target.suffix + ".part")
    tmp.write_bytes(_get(url))
    tmp.replace(target)
    return target


def paper(bench: Benchmark, cache: Path) -> Path:
    version = bench.minecraft
    build = str(bench.server.get("paper_build", "latest"))
    api = f"https://fill.papermc.io/v3/projects/paper/versions/{version}/builds/{build}"
    info = json.loads(_get(api))
    download = info["downloads"]["server:default"]
    return _download(download["url"], cache / "paper" / download["name"])


def modrinth(project: str, loader: str, game_version: str, target_dir: Path,
             version: str | None = None, file_regex: str = r".*\.jar$", force: bool = False) -> Path:
    query = urllib.parse.urlencode({"loaders": json.dumps([loader]), "game_versions": json.dumps([game_version])})
    versions = json.loads(_get(f"https://api.modrinth.com/v2/project/{project}/version?{query}"))
    if version:
        versions = [v for v in versions if v["version_number"] == version]
    if not versions:
        raise RuntimeError(f"No Modrinth release of {project} {version or ''} for {loader} {game_version}")
    pattern = re.compile(file_regex)
    files = [f for f in versions[0]["files"] if pattern.search(f["filename"])]
    if not files:
        raise RuntimeError(f"No file matching {pattern.pattern} in {project} {versions[0]['version_number']}")
    return _download(files[0]["url"], target_dir / files[0]["filename"], force)


def build_from_git(client: Client, cache: Path, force: bool = False) -> Path:
    """Builds the client jar from a pinned commit; the result is cached per commit."""
    dl = client.download
    commit = dl["commit"]
    out = cache / "clients" / client.id / f"{client.id}-{commit[:10]}.jar"
    if out.exists() and not force:
        return out
    src = cache / "clients" / client.id / f"src-{commit[:10]}"
    if not (src / ".git").exists():
        src.mkdir(parents=True, exist_ok=True)
        for cmd in (["git", "init", "-q"], ["git", "remote", "add", "origin", dl["git"]],
                    ["git", "fetch", "-q", "--depth", "1", "origin", commit], ["git", "checkout", "-q", "FETCH_HEAD"]):
            subprocess.run(cmd, cwd=src, check=True)
    print(f"[fetch] building {client.id} at {commit[:10]}: {dl['build']}")
    subprocess.run(dl["build"], cwd=src, shell=True, check=True, env=dict(os.environ))
    candidates = [p for p in sorted(src.glob(dl["artifact"])) if not re.search(r"-(sources|dev|javadoc)\.jar$", p.name)]
    if not candidates:
        raise FileNotFoundError(f"{client.id}: build produced no jar matching {dl['artifact']}")
    shutil.copy2(candidates[0], out)
    return out


def client_mod(bench: Benchmark, client: Client, cache: Path, force: bool = False) -> list[Path]:
    """The client jar plus its dependencies and any extra mod jars listed in the client config."""
    jars = []
    dl = client.download
    if "git" in dl:
        jars.append(build_from_git(client, cache, force))
    elif "url" in dl:
        url = dl["url"].format(minecraft=bench.minecraft)
        name = dl.get("filename", f"{client.id}.jar").format(minecraft=bench.minecraft)
        jars.append(_download(url, cache / "clients" / client.id / name, force))
    elif "path" in dl:
        jars.append((bench.root / dl["path"]).resolve())
    for dep in client.dependencies:
        jars.append(modrinth(dep["modrinth"], dep.get("loader", "fabric"), bench.minecraft,
                             cache / "clients" / client.id / "deps", dep.get("version"),
                             dep.get("file_regex", r".*\.jar$"), force))
    for extra in client.mods:
        jars.append((bench.root / extra).resolve())
    return jars


def anticheat(bench: Benchmark, ac: AntiCheat, cache: Path, force: bool = False) -> list[Path]:
    jars = [(bench.root / jar).resolve() for jar in ac.jars]
    dl = ac.download
    if "modrinth" in dl:
        jars.append(modrinth(dl["modrinth"], dl.get("loader", "paper"), bench.minecraft, cache / "anticheats" / ac.id,
                             dl.get("version"), dl.get("file_regex", r".*\.jar$"), force))
    elif "url" in dl:
        name = dl.get("filename", Path(urllib.parse.urlparse(dl["url"]).path).name)
        jar = _download(dl["url"], cache / "anticheats" / ac.id / name, force)
        if dl.get("sha256") and hashlib.sha256(jar.read_bytes()).hexdigest() != dl["sha256"].lower():
            jar.unlink()
            raise RuntimeError(f"anticheat {ac.id}: {name} does not match the sha256 in its config")
        jars.append(jar)
    for dep in ac.dependencies:
        deps_dir = cache / "anticheats" / ac.id / "deps"
        if "modrinth" in dep:
            jars.append(modrinth(dep["modrinth"], dep.get("loader", "paper"), bench.minecraft, deps_dir,
                                 dep.get("version"), dep.get("file_regex", r".*\.jar$"), force))
        else:
            name = dep.get("filename", Path(urllib.parse.urlparse(dep["url"]).path).name)
            jars.append(_download(dep["url"], deps_dir / name, force))
    for jar in jars:
        if not jar.exists():
            raise FileNotFoundError(f"anticheat {ac.id}: jar {jar} not found")
    return jars


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
