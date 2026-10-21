"""Expands scenarios x client variants x repetitions into the trial list both driver and collector read."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path
from typing import Any

from .config import Benchmark, CheatMapping, Client, Scenario, Variant

INSTANT_ACTIONS = {"server", "look", "slot"}


def expand_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for action in actions:
        if action.get("type") == "repeat":
            for _ in range(int(action.get("times", 1))):
                out.extend(expand_actions(action.get("actions", [])))
            continue
        action = dict(action)
        if action.get("type") in INSTANT_ACTIONS:
            action.setdefault("ticks", 1)
        out.append(action)
    return out


def _target_type(spec: dict) -> str:
    kind = spec.get("type", "minecraft:husk")
    return "minecraft:player" if kind == "player" else kind


def _trial(scenario: Scenario, variant: str, phase: str, rep: int, modules: list[dict], actions: list[dict]) -> dict:
    return {
        "id": f"{scenario.id}.{variant}.r{rep}",
        "scenario": scenario.id,
        "category": scenario.category,
        "variant": variant,
        "phase": phase,
        "rep": rep,
        "arena": scenario.arena,
        "loadout": scenario.loadout,
        "targets": scenario.targets,
        "target_types": sorted({_target_type(t) for t in scenario.targets}),
        "modules": modules,
        "actions": expand_actions(actions),
        "metric": scenario.metric,
        "advantage": scenario.advantage,
    }


def module_dump_file(bench: Benchmark, client: Client) -> Path:
    """Latest module dump of the client; every run refreshes it, `./bench discover` creates the first one."""
    return bench.root / "cache" / "clients" / client.id / "modules.json"


def setting_options(dump: list[dict], module: str, setting: str) -> list[str]:
    """Options of a setting in a module dump (Meteor dumps setting names, LiquidBounce full value keys)."""
    for entry in dump:
        if str(entry.get("name", "")).lower() != module.lower():
            continue
        for s in entry.get("settings", []):
            name = str(s.get("name", "")).lower()
            key = str(s.get("key", "")).lower()
            if name == setting.lower() or key == f"{str(entry.get('key', '')).lower()}.{setting.lower()}":
                return [str(o) for o in s.get("options") or []]
    return []


def expand_variants(mapping: CheatMapping, dump: list[dict] | None, client_id: str) -> list[Variant]:
    """Hand-written variants plus one generated variant per mode option; duplicates of hand-written ones are skipped."""
    variants = list(mapping.variants)
    if not mapping.auto_modes:
        return variants
    if dump is None:
        print(f"[plan] {client_id}: no module dump yet, run './bench discover --clients {client_id}' to test every "
              f"{mapping.module} mode; using the hand-written variants only", file=sys.stderr)
        return variants
    options = setting_options(dump, mapping.module, mapping.auto_modes)
    if not options:
        print(f"[plan] {client_id}: {mapping.module} has no setting '{mapping.auto_modes}' with options", file=sys.stderr)
    covered = {v.settings.get(mapping.auto_modes, "").lower() for v in variants if set(v.settings) == {mapping.auto_modes}}
    names = {v.name for v in variants}
    excluded = {m.lower() for m in mapping.exclude_modes}
    for option in options:
        if option.lower() in excluded or option.lower() in covered:
            continue
        name = re.sub(r"[^a-z0-9-]+", "_", option.lower()).strip("_") or "mode"
        while name in names:
            name += "_auto"
        names.add(name)
        variants.append(Variant(name, {**mapping.auto_base, mapping.auto_modes: option}, {}))
    return variants


def build_trials(bench: Benchmark, client: Client, scenario_filter: set[str] | None = None) -> list[dict]:
    """Baseline + every variant per scenario, shuffled within each repetition block (seeded)."""
    dump_file = module_dump_file(bench, client)
    dump = json.loads(dump_file.read_text()) if dump_file.exists() else None
    expanded = {cheat: expand_variants(mapping, dump, client.id) for cheat, mapping in client.cheats.items()}
    trials: list[dict] = []
    for rep in range(1, bench.repetitions + 1):
        block: list[dict] = []
        for scenario in bench.scenarios:
            if scenario_filter and scenario.id not in scenario_filter:
                continue
            mapping = client.cheats.get(scenario.cheat)
            if mapping is None:
                if rep == 1:
                    print(f"[plan] {client.id}: no mapping for cheat '{scenario.cheat}', skipping scenario {scenario.id}", file=sys.stderr)
                continue
            cheat_actions = scenario.cheat_actions if scenario.cheat_actions is not None else scenario.actions
            for strategy in scenario.baselines:
                block.append(_trial(scenario, f"baseline-{strategy['name']}", "baseline", rep, [], strategy["actions"]))
            for variant in expanded[scenario.cheat]:
                modules = [{"name": mapping.module, "settings": variant.settings}]
                modules += [{"name": name, "settings": settings} for name, settings in variant.extra_modules.items()]
                block.append(_trial(scenario, variant.name, "cheat", rep, modules, cheat_actions))
        random.Random(bench.seed * 1000 + rep).shuffle(block)
        trials.extend(block)
    return trials


def build_plan(bench: Benchmark, client: Client, run_id: str, trials: list[dict], paths: dict[str, str]) -> dict:
    timing = bench.timing
    return {
        "run_id": run_id,
        "client": {"id": client.id, "adapter": client.adapter, "adapter_options": client.adapter_options},
        "seed": bench.seed,
        "progress_file": paths["progress"],
        "client_log": paths["client_log"],
        "modules_dump": paths["modules_dump"],
        "start_delay_ticks": int(timing.get("start_delay_ticks", 100)),
        "setup_ticks": int(timing.get("setup_ticks", 30)),
        "cooldown_ticks": int(timing.get("cooldown_ticks", 40)),
        "reconnect_between_trials": bool(timing.get("reconnect_between_trials", True)),
        "rejoin_settle_ticks": int(timing.get("rejoin_settle_ticks", 40)),
        "server_address": f"127.0.0.1:{bench.server.get('port', 25599)}",
        "managed_modules": client.managed_modules(),
        "trials": trials,
    }


def estimate_seconds(plan: dict) -> float:
    ticks = plan["start_delay_ticks"]
    # A rejoin costs roughly the settle time plus ~3 s for login and chunk loading.
    rejoin = plan["rejoin_settle_ticks"] + 60 if plan["reconnect_between_trials"] else 0
    for trial in plan["trials"]:
        ticks += rejoin + plan["setup_ticks"] + plan["cooldown_ticks"] + sum(max(1, a.get("ticks", 1)) for a in trial["actions"]) + 2
    return ticks / 20
