"""Loads benchmark.toml and the client / anticheat / scenario definitions under config/."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Variant:
    name: str
    settings: dict[str, str]
    extra_modules: dict[str, dict[str, str]]


@dataclass
class CheatMapping:
    cheat: str
    module: str
    variants: list[Variant]
    # Every option of this setting (read from the client's module dump) becomes a variant of its own.
    auto_modes: str | None = None
    exclude_modes: list[str] = field(default_factory=list)
    # Settings applied to every generated variant, e.g. to make a mode usable in the scenario.
    auto_base: dict[str, str] = field(default_factory=dict)


@dataclass
class Client:
    id: str
    name: str
    adapter: str
    adapter_options: dict[str, str]
    download: dict[str, Any]
    cheats: dict[str, CheatMapping]
    mods: list[str]
    dependencies: list[dict[str, Any]]
    jvm_args: list[str]
    always_disable: list[str]

    def managed_modules(self) -> list[str]:
        names: list[str] = list(self.always_disable)
        for mapping in self.cheats.values():
            names.append(mapping.module)
            for variant in mapping.variants:
                names.extend(variant.extra_modules)
        return sorted(set(names))


@dataclass
class AntiCheat:
    id: str
    name: str
    download: dict[str, Any]
    flag_sources: list[dict[str, Any]]
    files: dict[str, Path]
    jars: list[str]
    plugin: str | None
    # Stock alert thresholds: [{group, checks, alert_after}] plus name aliases, for "would alert by default".
    default_alerts: list[dict[str, Any]]
    default_alert_aliases: dict[str, str]
    # Further plugins the anticheat needs on the server, e.g. ProtocolLib: [{modrinth, version, ...} or {url, filename}].
    dependencies: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    category: str
    cheat: str
    arena: str
    description: str
    metric: str
    advantage: str
    actions: list[dict[str, Any]]
    baseline_actions: list[dict[str, Any]] | None
    cheat_actions: list[dict[str, Any]] | None
    loadout: list[str]
    targets: list[dict[str, Any]]
    # Legal ways to play the situation without cheats; the analysis compares against the best one.
    baselines: list[dict[str, Any]]


@dataclass
class Benchmark:
    root: Path
    name: str
    minecraft: str
    seed: int
    repetitions: int
    grace_ticks: int
    categories: list[str]
    client_ids: list[str]
    anticheat_ids: list[str]
    server: dict[str, Any]
    client: dict[str, Any]
    timing: dict[str, Any]
    scoring: dict[str, float]
    parallel: dict[str, Any] = field(default_factory=dict)
    clients: dict[str, Client] = field(default_factory=dict)
    anticheats: dict[str, AntiCheat] = field(default_factory=dict)
    scenarios: list[Scenario] = field(default_factory=list)

    @property
    def config_dir(self) -> Path:
        return self.root / "config"


def _str_settings(table: dict[str, Any]) -> dict[str, str]:
    return {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in table.items()}


def load_client(path: Path) -> Client:
    data = tomllib.loads(path.read_text())
    cheats: dict[str, CheatMapping] = {}
    for cheat_id, mapping in data.get("cheats", {}).items():
        variants = []
        for name, settings in mapping.get("variants", {}).items():
            settings = dict(settings)
            extra = {module: _str_settings(s) for module, s in settings.pop("with", {}).items()}
            variants.append(Variant(name, _str_settings(settings), extra))
        cheats[cheat_id] = CheatMapping(cheat_id, mapping["module"], variants, mapping.get("auto_modes"),
                                        list(mapping.get("exclude_modes", [])), _str_settings(mapping.get("auto_base", {})))
    return Client(
        id=data["id"],
        name=data.get("name", data["id"]),
        adapter=data.get("adapter", "none"),
        adapter_options={k: str(v) for k, v in data.get("adapter_options", {}).items()},
        download=data.get("download", {}),
        cheats=cheats,
        mods=list(data.get("mods", [])),
        dependencies=list(data.get("dependencies", [])),
        jvm_args=[str(a) for a in data.get("jvm_args", [])],
        always_disable=list(data.get("always_disable", [])),
    )


def load_anticheat(path: Path) -> AntiCheat:
    data = tomllib.loads(path.read_text())
    return AntiCheat(
        id=data["id"],
        name=data.get("name", data["id"]),
        download=data.get("download", {}),
        flag_sources=list(data.get("flag_sources", [])),
        files={target: path.parent / source for target, source in data.get("files", {}).items()},
        jars=list(data.get("jars", [])),
        plugin=data.get("plugin"),
        default_alerts=list(data.get("default_alerts", [])),
        default_alert_aliases=dict(data.get("default_alert_aliases", {})),
        dependencies=list(data.get("dependencies", [])),
    )


def load_scenarios(path: Path, category: str) -> list[Scenario]:
    data = tomllib.loads(path.read_text())
    scenarios = []
    for s in data.get("scenario", []):
        if s.get("advantage") not in ("higher", "lower"):
            raise ValueError(f"{path}: scenario {s.get('id')} needs advantage = 'higher' or 'lower'")
        scenarios.append(Scenario(
            id=s["id"],
            category=s.get("category", category),
            cheat=s["cheat"],
            arena=s["arena"],
            description=s.get("description", ""),
            metric=s["metric"],
            advantage=s["advantage"],
            actions=s.get("actions", []),
            baseline_actions=s.get("baseline_actions"),
            cheat_actions=s.get("cheat_actions"),
            loadout=list(s.get("loadout", [])),
            targets=list(s.get("targets", [])),
            baselines=list(s.get("baselines") or [{"name": "default", "actions": s.get("baseline_actions") or s.get("actions", [])}]),
        ))
    return scenarios


def load_benchmark(path: Path) -> Benchmark:
    path = path.resolve()
    data = tomllib.loads(path.read_text())
    bench = Benchmark(
        root=path.parent,
        name=data.get("name", "acbench"),
        minecraft=data["minecraft"],
        seed=int(data.get("seed", 1)),
        repetitions=int(data.get("repetitions", 3)),
        grace_ticks=int(data.get("grace_ticks", 40)),
        categories=list(data.get("categories", ["movement", "combat"])),
        client_ids=list(data.get("clients", [])),
        anticheat_ids=list(data.get("anticheats", ["none"])),
        server=data.get("server", {}),
        client=data.get("client", {}),
        timing=data.get("timing", {}),
        scoring=data.get("scoring", {"detection": 0.5, "false_positives": 0.35, "mitigation": 0.15}),
        parallel=data.get("parallel", {}),
    )
    cfg = bench.config_dir
    for client_id in bench.client_ids:
        bench.clients[client_id] = load_client(cfg / "clients" / f"{client_id}.toml")
    for ac_id in bench.anticheat_ids:
        bench.anticheats[ac_id] = load_anticheat(cfg / "anticheats" / f"{ac_id}.toml")
    for category in bench.categories:
        bench.scenarios.extend(load_scenarios(cfg / "scenarios" / f"{category}.toml", category))
    return bench
