"""Turns raw server/client event logs into per-trial rows and aggregated benchmark results."""
from __future__ import annotations

import csv
import json
import statistics
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REFERENCE_AC = "none"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def load_default_rules(ac_dir: Path, ac_id: str) -> dict | None:
    """Stock alert thresholds of the anticheat: saved with the run, else taken from config/anticheats/<id>.toml."""
    saved = ac_dir / "anticheat.json"
    if saved.exists():
        data = json.loads(saved.read_text())
    else:
        config = ac_dir.parents[3] / "config" / "anticheats" / f"{ac_id}.toml"
        data = tomllib.loads(config.read_text()) if config.exists() else {}
    return data if data.get("default_alerts") else None


def default_alert_tick(flags: list[dict], rules: dict) -> int | None:
    """Tick at which the anticheat would have alerted with its stock thresholds, replaying every captured violation."""
    aliases = {k.lower(): v.lower() for k, v in rules.get("default_alert_aliases", {}).items()}
    counts: dict[str, int] = defaultdict(int)
    for flag in sorted(flags, key=lambda f: f["tick"]):
        check = (flag.get("check") or "").lower()
        names = (check, aliases.get(check, check))
        for group in rules["default_alerts"]:
            if any(entry.lower() in name for entry in group["checks"] for name in names):
                if group.get("by") == "vl":
                    # Anticheats that weight violations (e.g. Intave) alert once the reported level reaches the threshold.
                    try:
                        reached = float(flag.get("vl")) >= float(group["alert_after"])
                    except (TypeError, ValueError):
                        reached = False
                else:
                    counts[group["group"]] += 1
                    reached = counts[group["group"]] >= int(group["alert_after"])
                if reached:
                    return flag["tick"]
    return None


def trial_rows(unit_dir: Path, client_id: str, ac_id: str, grace_ticks: int, ignore_players: set[str] | None = None,
               rules: dict | None = None) -> tuple[list[dict], dict]:
    """Rows for one server's worth of trials: a whole client × anticheat run, or one shard of it.

    Ticks are only comparable within one server, so flags are attributed per unit before units are merged.
    """
    plan = json.loads((unit_dir / "plan.json").read_text())
    trials = {t["id"]: t for t in plan["trials"]}
    events = load_jsonl(unit_dir / "server-events.jsonl")
    client_events = load_jsonl(unit_dir / "client-events.jsonl")

    prepared = {e["trial"]: e for e in client_events if e.get("type") == "trial_prepared"}
    ends = {e["trial"]: e for e in events if e.get("type") == "trial_end"}
    # Flags against the target bot are about the bot standing in as a target, not about the cheater.
    flags = [e for e in events if e.get("type") == "flag" and e.get("player") not in (ignore_players or set())]
    begins = {e["trial"]: e for e in events if e.get("type") == "trial_begin"}
    kicks = defaultdict(list)
    kick_ticks = {}
    for e in events:
        if e.get("type") == "kick" and e.get("trial"):
            kicks[e["trial"]].append(e.get("reason", ""))
            kick_ticks.setdefault(e["trial"], e["tick"])

    rows, attributed = [], set()
    for trial_id, trial in trials.items():
        end = ends.get(trial_id)
        row: dict[str, Any] = {
            "client": client_id, "anticheat": ac_id, "trial": trial_id, "scenario": trial["scenario"],
            "category": trial["category"], "variant": trial["variant"], "phase": trial["phase"], "rep": trial["rep"],
            "metric": trial["metric"], "advantage": trial["advantage"], "completed": end is not None,
            "kicked": bool(kicks.get(trial_id)), "kick_reasons": kicks.get(trial_id, []),
            "unit": unit_dir.name,
        }
        prep = prepared.get(trial_id, {})
        row["setup_failed"] = prep.get("failed", [])
        not_enabled = [m for m, state in prep.get("enabled", {}).items() if state is False]
        if not_enabled:
            row["setup_failed"] = row["setup_failed"] + [f"{m}: not enabled" for m in not_enabled]
        if end is None:
            # A kicked trial has no end measurement, but flags raised before the kick still belong to it.
            begin = begins.get(trial_id)
            if begin is not None and trial_id in kick_ticks:
                mine = [i for i, f in enumerate(flags)
                        if begin["tick"] <= f["tick"] <= kick_ticks[trial_id] and f.get("player") in (None, begin.get("player"))]
                attributed.update(mine)
                row["flags"] = len(mine)
                row["checks"] = dict(Counter(flags[i].get("check") or "?" for i in mine))
                if rules:
                    row["default_alert"] = default_alert_tick([flags[i] for i in mine], rules) is not None
            rows.append(row)
            continue
        begin_tick, end_tick = end["begin_tick"], end["tick"]
        mine = [i for i, f in enumerate(flags)
                if begin_tick <= f["tick"] <= end_tick + grace_ticks and f.get("player") in (None, end.get("player"))]
        attributed.update(mine)
        trial_flags = [flags[i] for i in mine]
        row.update({
            "begin_tick": begin_tick,
            "end_tick": end_tick,
            "flags": len(trial_flags),
            "checks": dict(Counter(f.get("check") or "?" for f in trial_flags)),
            "first_flag_ticks": min((f["tick"] - begin_tick for f in trial_flags), default=None),
            "default_alert": None,
            "default_alert_ticks": None,
            "server_wall_ms": end["time_ms"] - begins[trial_id]["time_ms"] if trial_id in begins else None,
            "value": end["metrics"].get(trial["metric"]),
            "metrics": end["metrics"],
            "client_stats": end.get("client", {}),
        })
        if rules:
            alert_tick = default_alert_tick(trial_flags, rules)
            row["default_alert"] = alert_tick is not None
            row["default_alert_ticks"] = None if alert_tick is None else alert_tick - begin_tick
        rows.append(row)

    info = {
        "unattributed_flags": len(flags) - len(attributed),
        "joins": sum(1 for e in events if e.get("type") == "join"),
        "server_ready": next((e for e in events if e.get("type") == "server_ready"), None),
        "done": any(e.get("type") == "done" for e in events),
        "errors": [e for e in events + client_events if e.get("type") == "error"][:50],
    }
    return rows, info


# A unit counts as overloaded when the median baseline trial ran slower than this; cheat trials are left out
# because a timer cheat changes the client's tick rate on purpose.
MIN_TICKS_PER_SECOND = 18.5
MAX_SERVER_MSPT = 40.0


def measurement_quality(rows: list[dict]) -> dict:
    """How well client and server kept up during legal (baseline) trials: guards parallel runs against overload."""
    base = [r for r in rows if r["completed"] and r["phase"] == "baseline"]
    client_tps = [r["client_stats"]["ticks"] * 1000 / r["client_stats"]["wall_ms"] for r in base
                  if (r.get("client_stats") or {}).get("wall_ms") and r["client_stats"].get("ticks")]
    server_tps = [r["metrics"]["ticks"] * 1000 / r["server_wall_ms"] for r in base if r.get("server_wall_ms")]
    mspt = [r["metrics"]["avg_mspt"] for r in base if (r.get("metrics") or {}).get("avg_mspt") is not None]
    quality = {
        "client_tps": statistics.median(client_tps) if client_tps else None,
        "client_tps_min": min(client_tps) if client_tps else None,
        "server_tps": statistics.median(server_tps) if server_tps else None,
        "server_mspt": statistics.median(mspt) if mspt else None,
        "server_mspt_max": max(mspt) if mspt else None,
    }
    quality["overloaded"] = bool(
        (quality["client_tps"] is not None and quality["client_tps"] < MIN_TICKS_PER_SECOND)
        or (quality["server_tps"] is not None and quality["server_tps"] < MIN_TICKS_PER_SECOND)
        or (quality["server_mspt"] is not None and quality["server_mspt"] > MAX_SERVER_MSPT))
    return quality


# A legal (baseline) trial with an anticheat that reaches less than this share of the same strategy's result
# without anticheat means the bot was held back, e.g. frozen by setbacks. Such a run measures the setup, not cheats.
IMPAIRED_SHARE = 0.5
MAX_IMPAIRED_RATE = 0.25


def impaired_legal_play(rows: list[dict], client: str, anticheat: str) -> dict:
    """Compares every legal trial under the anticheat with the same strategy in the reference run."""
    reference: dict[tuple, list[float]] = defaultdict(list)
    for r in rows:
        if r["client"] == client and r["anticheat"] == REFERENCE_AC and r["phase"] == "baseline" and r["completed"]:
            reference[(r["scenario"], r["variant"])].append(r["value"])
    checked = impaired = 0
    examples = []
    for r in rows:
        if r["client"] != client or r["anticheat"] != anticheat or r["phase"] != "baseline" or not r["completed"]:
            continue
        ref = _mean(reference.get((r["scenario"], r["variant"]), []))
        if ref is None or r["value"] is None or abs(ref) < 0.5:
            continue  # nothing to compare against, or a metric that is legitimately ~0 (e.g. hits through walls)
        checked += 1
        worse = r["value"] < IMPAIRED_SHARE * ref if r["advantage"] == "higher" else r["value"] > ref / IMPAIRED_SHARE
        if worse:
            impaired += 1
            examples.append(r["trial"])
    rate = impaired / checked if checked else None
    return {"checked": checked, "impaired": impaired, "rate": rate, "examples": examples[:5],
            "invalid": bool(rate is not None and rate > MAX_IMPAIRED_RATE)}


def _mean(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def _no_effect_threshold(baseline: float | None) -> float:
    return max(0.05, 0.05 * abs(baseline or 0))


def aggregate(rows: list[dict], weights: dict[str, float]) -> dict:
    by_variant: dict[tuple, list[dict]] = defaultdict(list)
    by_baseline: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if not r["completed"] and not r["kicked"]:
            continue
        if r["phase"] == "baseline":
            by_baseline[(r["client"], r["anticheat"], r["scenario"])].append(r)
        else:
            by_variant[(r["client"], r["anticheat"], r["scenario"], r["variant"])].append(r)

    def completed(group: list[dict]) -> list[dict]:
        return [r for r in group if r["completed"]]

    def strategy_means(group: list[dict]) -> dict[str, float]:
        values: dict[str, list] = defaultdict(list)
        for r in completed(group):
            values[r["variant"]].append(r["value"])
        return {k: m for k, v in values.items() if (m := _mean(v)) is not None}

    # The best legal strategy per scenario, picked in the reference run, is the baseline everywhere: a cheat only
    # counts as an advantage when it beats the best way to play the situation without cheats.
    best_strategy: dict[tuple, str] = {}
    for (client, ac, scenario), group in by_baseline.items():
        means = strategy_means(group)
        if ac == REFERENCE_AC and means:
            sign = 1 if group[0]["advantage"] == "higher" else -1
            best_strategy[(client, scenario)] = max(means, key=lambda k: sign * means[k])

    def baseline_mean(client: str, ac: str, scenario: str) -> float | None:
        group = by_baseline.get((client, ac, scenario), [])
        means = strategy_means(group)
        if not means:
            return None
        chosen = best_strategy.get((client, scenario))
        if chosen in means:
            return means[chosen]
        sign = 1 if group[0]["advantage"] == "higher" else -1
        return max(means.values(), key=lambda v: sign * v)

    def raw_advantage_of(client: str, scenario: str, variant: str, sign: int) -> tuple[float | None, bool]:
        ref_cheat = _mean([r["value"] for r in completed(by_variant.get((client, REFERENCE_AC, scenario, variant), []))])
        ref_base = baseline_mean(client, REFERENCE_AC, scenario)
        if ref_cheat is None or ref_base is None:
            return None, False
        raw = sign * (ref_cheat - ref_base)
        return raw, raw > _no_effect_threshold(ref_base)

    # Strongest effect any ordinary variant of a scenario reaches without anticheat; reference for targeted bypasses.
    scenario_max: dict[tuple, float] = {}
    for (client, ac, scenario, variant), all_trials in by_variant.items():
        sign = 1 if all_trials[0]["advantage"] == "higher" else -1
        raw, effective = raw_advantage_of(client, scenario, variant, sign)
        if effective:
            scenario_max[(client, scenario)] = max(raw, scenario_max.get((client, scenario), raw))

    variants = []
    for (client, ac, scenario, variant), all_trials in sorted(by_variant.items()):
        # Kicked trials have no end measurement; they are reported separately and excluded from the metrics.
        kicked = [r for r in all_trials if r["kicked"]]
        group = completed(all_trials)
        sign = 1 if all_trials[0]["advantage"] == "higher" else -1
        cheat_mean = _mean([r["value"] for r in group])
        base = baseline_mean(client, ac, scenario)
        advantage = sign * (cheat_mean - base) if cheat_mean is not None and base is not None else None

        raw_advantage, effective = raw_advantage_of(client, scenario, variant, sign)
        # Targeted bypasses can only work against their anticheat (e.g. by abusing its setbacks), so they show no
        # effect in the reference run. They still count when they give an advantage with the anticheat installed.
        bypass_only = (not effective and ac != REFERENCE_AC and advantage is not None
                       and advantage > _no_effect_threshold(base))
        reference = raw_advantage if effective else scenario_max.get((client, scenario), advantage) if bypass_only else None
        retained = advantage / reference if reference and advantage is not None else None

        detected = [r for r in group if r.get("flags", 0) > 0]
        has_rules = any(r.get("default_alert") is not None for r in group)
        default_detected = [r for r in group if r.get("default_alert")]
        ttd = [r["first_flag_ticks"] / 20 for r in detected if r.get("first_flag_ticks") is not None]
        checks = Counter()
        for r in group:
            checks.update(r.get("checks", {}))
        variants.append({
            "client": client, "anticheat": ac, "scenario": scenario, "variant": variant,
            "category": all_trials[0]["category"], "metric": all_trials[0]["metric"], "advantage_direction": all_trials[0]["advantage"],
            "trials": len(group),
            "detected": len(detected),
            "detection_rate": len(detected) / len(group) if group else None,
            "default_detected": len(default_detected) if has_rules else None,
            "default_detection_rate": len(default_detected) / len(group) if group and has_rules else None,
            "median_time_to_flag_s": statistics.median(ttd) if ttd else None,
            "mean_flags": _mean([r.get("flags", 0) for r in group]),
            "top_checks": checks.most_common(4),
            "cheat_metric": cheat_mean,
            "baseline_metric": base,
            "baseline_strategy": best_strategy.get((client, scenario)),
            "advantage": advantage,
            "raw_advantage": raw_advantage,
            "effective": effective,
            "bypass_only": bypass_only,
            "valid": effective or bypass_only,
            "reference_advantage": reference,
            "retained_advantage": retained,
            "setup_issues": sorted({msg for r in group for msg in r.get("setup_failed", [])}),
            "kicks": len(kicked),
            "kick_reasons": sorted({reason for r in kicked for reason in r.get("kick_reasons", [])}),
            "flagged_before_kick": sum(1 for r in kicked if r.get("flags", 0) > 0),
            "kick_checks": sum((Counter(r.get("checks", {})) for r in kicked), Counter()).most_common(4),
        })

    baselines = []
    for (client, ac, scenario), group in sorted(by_baseline.items()):
        group = completed(group)
        if not group:
            continue
        flagged = [r for r in group if r.get("flags", 0) > 0]
        has_rules = any(r.get("default_alert") is not None for r in group)
        default_flagged = sum(1 for r in group if r.get("default_alert"))
        checks = Counter()
        for r in group:
            checks.update(r.get("checks", {}))
        baselines.append({
            "client": client, "anticheat": ac, "scenario": scenario, "category": group[0]["category"],
            "strategies": strategy_means(group), "chosen_strategy": best_strategy.get((client, scenario)),
            "trials": len(group), "flagged": len(flagged), "false_positive_rate": len(flagged) / len(group),
            "default_flagged": default_flagged if has_rules else None,
            "default_false_positive_rate": default_flagged / len(group) if has_rules else None,
            "mean_flags": _mean([r.get("flags", 0) for r in group]), "top_checks": checks.most_common(4),
            "baseline_metric": _mean([r["value"] for r in group]),
        })

    def strongest(vs: list[dict]) -> dict:
        """The setting a cheater would pick: most advantage left over, then least often detected."""
        return sorted(vs, key=lambda v: (-(v["retained_advantage"] if v["retained_advantage"] is not None else -9.0),
                                         v["detection_rate"] if v["detection_rate"] is not None else 1.0))[0]

    summaries = []
    for client, ac in sorted({(v["client"], v["anticheat"]) for v in variants}):
        if ac == REFERENCE_AC:
            continue
        mine = [v for v in variants if v["client"] == client and v["anticheat"] == ac]
        valid = [v for v in mine if v["valid"]]
        base = [b for b in baselines if b["client"] == client and b["anticheat"] == ac]
        # Every cheat type counts once, judged by its strongest setting, so clients with many settings per cheat
        # are scored on the same footing as clients with few.
        by_scenario: dict[str, list[dict]] = defaultdict(list)
        for v in valid:
            by_scenario[v["scenario"]].append(v)
        cheat_types = []
        for scenario, vs in sorted(by_scenario.items()):
            st = strongest(vs)
            cheat_types.append({
                "scenario": scenario, "category": st["category"], "strongest_variant": st["variant"],
                "detection_rate": st["detection_rate"], "default_detection_rate": st.get("default_detection_rate"),
                "retained_advantage": st["retained_advantage"], "median_time_to_flag_s": st["median_time_to_flag_s"],
                "variants": len(vs),
                "blocked_variants": sum(1 for v in vs if v["retained_advantage"] is not None and v["retained_advantage"] <= 0.25),
            })
        summary: dict[str, Any] = {"client": client, "anticheat": ac, "valid_variants": len(valid),
                                   "invalid_variants": len(mine) - len(valid), "cheat_types": cheat_types}
        for category in sorted({c["category"] for c in cheat_types} | {"all"}):
            cs = [c for c in cheat_types if category in ("all", c["category"])]
            bs = [b for b in base if category in ("all", b["category"])]
            retained = [min(1.0, max(0.0, c["retained_advantage"])) for c in cs if c["retained_advantage"] is not None]
            baseline_trials = sum(b["trials"] for b in bs)
            ttd = [c["median_time_to_flag_s"] for c in cs if c["median_time_to_flag_s"] is not None]
            default_rates = [c["default_detection_rate"] for c in cs if c["default_detection_rate"] is not None]
            default_fp = [b for b in bs if b.get("default_flagged") is not None]
            summary[category] = {
                "cheat_types": len(cs),
                "detection_rate": _mean([c["detection_rate"] for c in cs]),
                "default_detection_rate": _mean(default_rates) if default_rates else None,
                "median_time_to_flag_s": statistics.median(ttd) if ttd else None,
                "false_positive_rate": sum(b["flagged"] for b in bs) / baseline_trials if baseline_trials else None,
                "default_false_positive_rate": (sum(b["default_flagged"] for b in default_fp) / sum(b["trials"] for b in default_fp)
                                                if default_fp else None),
                "mitigation": 1 - statistics.fmean(retained) if retained else None,
            }
        overall = summary["all"]
        parts = {
            "detection": overall["detection_rate"],
            "false_positives": None if overall["false_positive_rate"] is None else 1 - overall["false_positive_rate"],
            "mitigation": overall["mitigation"],
        }
        used = {k: w for k, w in weights.items() if parts.get(k) is not None}
        summary["score"] = 100 * sum(parts[k] * w for k, w in used.items()) / sum(used.values()) if used else None
        summaries.append(summary)

    return {"summaries": summaries, "variants": variants, "baselines": baselines}


DEFAULT_SCORING = {"detection": 0.5, "false_positives": 0.35, "mitigation": 0.15}


def compute_run(run_dir: Path) -> tuple[dict, list[dict]]:
    """Aggregates whatever a run has produced so far; works on finished and on still running runs."""
    meta_file = run_dir / "run.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {"run_id": run_dir.name}
    rows, infos = [], {}
    ignore = {meta["target_player"]} if meta.get("target_player") else None
    for client_dir in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        for ac_dir in sorted(p for p in client_dir.iterdir() if (p / "plan.json").exists()):
            rules = load_default_rules(ac_dir, ac_dir.name)
            # Parallel runs split a client × anticheat run into shards, each with its own server and event log.
            units = sorted(p.parent for p in ac_dir.glob("shards/*/plan.json")) or [ac_dir]
            pair_rows, unit_infos = [], []
            for unit in units:
                r, info = trial_rows(unit, client_dir.name, ac_dir.name, meta.get("grace_ticks", 40), ignore, rules)
                pair_rows.extend(r)
                unit_infos.append(info)
            rows.extend(pair_rows)
            infos[f"{client_dir.name}/{ac_dir.name}"] = {
                "unattributed_flags": sum(i["unattributed_flags"] for i in unit_infos),
                "joins": sum(i["joins"] for i in unit_infos),
                "server_ready": unit_infos[0]["server_ready"],
                "done": all(i["done"] for i in unit_infos),
                "errors": [e for i in unit_infos for e in i["errors"]][:50],
                "shards": len(units) if units != [ac_dir] else 0,
                "quality": measurement_quality(pair_rows),
                "shard_quality": {u.name: measurement_quality([r for r in pair_rows if r["unit"] == u.name])
                                  for u in units} if units != [ac_dir] else {},
            }
    for key, info in infos.items():
        client, anticheat = key.split("/", 1)
        if anticheat != REFERENCE_AC:
            info["legal_play"] = impaired_legal_play(rows, client, anticheat)
    result = aggregate(rows, meta.get("scoring", DEFAULT_SCORING))
    result["meta"] = meta
    result["runs"] = infos
    return result, rows


def analyze_run(run_dir: Path) -> dict:
    result, rows = compute_run(run_dir)
    (run_dir / "results.json").write_text(json.dumps(result, indent=2, default=str))
    with (run_dir / "trials.csv").open("w", newline="") as f:
        fields = ["client", "anticheat", "trial", "scenario", "category", "variant", "phase", "rep", "completed",
                  "flags", "first_flag_ticks", "metric", "value", "kicked", "checks", "setup_failed"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "checks": json.dumps(row.get("checks", {})), "setup_failed": "; ".join(row.get("setup_failed", []))})
    return result
