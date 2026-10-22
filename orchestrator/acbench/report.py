"""Renders results.json as report.md and a self-contained report.html."""
from __future__ import annotations

import html
from pathlib import Path


def _pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.0f} %"


def _num(value: float | None, digits: int = 2) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def _checks(top: list) -> str:
    return ", ".join(f"{name} ×{count}" for name, count in top) or "–"


def _ac_names(result: dict) -> list[str]:
    acs = sorted({v["anticheat"] for v in result["variants"]})
    return (["none"] if "none" in acs else []) + [a for a in acs if a != "none"]


def markdown(result: dict) -> str:
    meta = result["meta"]
    out = [f"# AntiCheat Benchmark – {meta['name']}", "",
           f"Run `{meta['run_id']}` · Minecraft {meta['minecraft']} · {meta['repetitions']} repetitions · "
           f"clients: {', '.join(meta['clients'])} · anticheats: {', '.join(meta['anticheats'])}", ""]

    out += ["## Summary", "",
            "Per cheat type the strongest setting counts; every cheat type weighs the same. Detection = any flag; "
            "default alert = the anticheat's stock thresholds would have alerted within the ~5 s trial.", "",
            "| Client | AntiCheat | Score | Detection | Default alert | False positives | Mitigation | Median time to flag | Valid variants |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in result["summaries"]:
        a = s["all"]
        out.append(f"| {s['client']} | {s['anticheat']} | {_num(s['score'], 0)} | {_pct(a['detection_rate'])} | {_pct(a.get('default_detection_rate'))} | "
                   f"{_pct(a['false_positive_rate'])} | {_pct(a['mitigation'])} | {_num(a['median_time_to_flag_s'], 1)} s | "
                   f"{s['valid_variants']} (+{s['invalid_variants']} without effect) |")
    out.append("")
    for s in result["summaries"]:
        cats = [c for c in s if isinstance(s[c], dict) and c != "all"]
        if cats:
            out.append(f"**{s['client']} vs {s['anticheat']}** by category: " + "; ".join(
                f"{c}: detection {_pct(s[c]['detection_rate'])}, FP {_pct(s[c]['false_positive_rate'])}, mitigation {_pct(s[c]['mitigation'])}" for c in cats))
            out.append("")

    out += ["## Cheats", "",
            "Detection = share of cheat trials with at least one flag. Advantage = cheat minus baseline on the scenario metric "
            "(sign-normalized). Retained = advantage with the anticheat relative to the advantage without any anticheat.", ""]
    for client in sorted({v["client"] for v in result["variants"]}):
        out += [f"### {client}", "", "| Scenario | Variant | AntiCheat | Detection | Time to flag | Advantage (raw) | Retained | Top checks | Notes |",
                "|---|---|---|---:|---:|---:|---:|---|---|"]
        for v in sorted((v for v in result["variants"] if v["client"] == client), key=lambda v: (v["category"], v["scenario"], v["variant"], v["anticheat"] != "none", v["anticheat"])):
            notes = []
            if v.get("bypass_only"):
                notes.append("targeted bypass: advantage only with this anticheat, compared against the strongest ordinary variant")
            elif not v["effective"]:
                notes.append("no measurable effect without anticheat")
            if v["setup_issues"]:
                notes.append("setup: " + "; ".join(v["setup_issues"]))
            if v["kicks"]:
                notes.append(f"{v['kicks']} kicked ({'; '.join(v['kick_reasons'])}), flagged before kick: {v['flagged_before_kick']}/{v['kicks']}"
                             + (f" [{_checks(v['kick_checks'])}]" if v["kick_checks"] else ""))
            out.append(f"| {v['scenario']} | {v['variant']} | {v['anticheat']} | {_pct(v['detection_rate'])} ({v['detected']}/{v['trials']}) | "
                       f"{_num(v['median_time_to_flag_s'], 1)} s | {_num(v['advantage'])} ({_num(v['raw_advantage'])}) | {_pct(v['retained_advantage'])} | "
                       f"{_checks(v['top_checks'])} | {', '.join(notes)} |")
        out.append("")

    out += ["## False positives (baseline trials, cheat off)", "", "| Client | AntiCheat | Scenario | Flagged | Top checks |", "|---|---|---|---:|---|"]
    for b in result["baselines"]:
        if b["anticheat"] != "none":
            out.append(f"| {b['client']} | {b['anticheat']} | {b['scenario']} | {_pct(b['false_positive_rate'])} ({b['flagged']}/{b['trials']}) | {_checks(b['top_checks'])} |")
    out.append("")
    out += ["## Run health", ""]
    for key, info in result["runs"].items():
        q = info.get("quality") or {}
        load = (f", client {_num(q.get('client_tps'), 1)} ticks/s, server {_num(q.get('server_tps'), 1)} ticks/s"
                + (" **OVERLOADED – repeat with fewer workers**" if q.get("overloaded") else "")) if q else ""
        legal = info.get("legal_play") or {}
        if legal.get("invalid"):
            load += (f" **INVALID: legal play impaired in {legal['impaired']}/{legal['checked']} baseline trials "
                     f"(bot held back or frozen), results of this pair do not measure the cheats**")
        reused = f", reused from {info['reused_from']}" if info.get("reused_from") else ""
        out.append(f"- `{key}`: finished={info['done']}, shards={info.get('shards') or 1}, joins={info.get('joins', '?')}, "
                   f"unattributed flags={info['unattributed_flags']}, errors={len(info['errors'])}{load}{reused}")
    out.append("")
    return "\n".join(out)


CSS = """
:root { --bg:#fbfbfa; --fg:#1d1d1f; --muted:#6b6b70; --line:#e2e2e0; --card:#ffffff;
        --good:#1f8a4c; --mid:#b7791f; --bad:#c0392b; --chip:#f0f0ee; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
        --bg:#141416; --fg:#ececee; --muted:#9a9aa2; --line:#2c2c31; --card:#1c1c20;
        --good:#4cc283; --mid:#e0a84a; --bad:#ef6b5e; --chip:#26262b; } }
:root[data-theme="dark"] { --bg:#141416; --fg:#ececee; --muted:#9a9aa2; --line:#2c2c31; --card:#1c1c20;
        --good:#4cc283; --mid:#e0a84a; --bad:#ef6b5e; --chip:#26262b; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:1180px; margin:0 auto; padding:32px 16px 64px; }
h1 { font-size:26px; margin:0 0 4px; } h2 { font-size:19px; margin:36px 0 12px; } h3 { font-size:16px; margin:24px 0 8px; }
.sub { color:var(--muted); margin:0 0 24px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }
.card .score { font-size:34px; font-weight:650; font-variant-numeric:tabular-nums; }
.card dl { display:grid; grid-template-columns:auto auto; gap:2px 12px; margin:8px 0 0; }
.card dt { color:var(--muted); } .card dd { margin:0; text-align:right; font-variant-numeric:tabular-nums; }
.wrap { overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--card); }
table { border-collapse:collapse; width:100%; font-size:13.5px; }
th, td { padding:7px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; }
th { color:var(--muted); font-weight:600; position:sticky; top:0; background:var(--card); }
td.n { text-align:right; font-variant-numeric:tabular-nums; }
tr:last-child td { border-bottom:none; }
.good { color:var(--good); } .mid { color:var(--mid); } .bad { color:var(--bad); }
.chip { display:inline-block; background:var(--chip); border-radius:6px; padding:0 6px; margin:1px 2px 1px 0; font-size:12px; }
.note { color:var(--muted); font-size:12.5px; white-space:normal; min-width:180px; }
p.legend { color:var(--muted); font-size:13.5px; max-width:820px; }
"""


def _cls(value: float | None, good_high: bool = True) -> str:
    if value is None:
        return ""
    v = value if good_high else 1 - value
    return "good" if v >= 0.75 else "mid" if v >= 0.4 else "bad"


def _cell(text: str, cls: str = "", numeric: bool = True) -> str:
    classes = " ".join(c for c in ("n" if numeric else "", cls) if c)
    return f'<td class="{classes}">{text}</td>' if classes else f"<td>{text}</td>"


def html_report(result: dict) -> str:
    e = html.escape
    meta = result["meta"]
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
             f"<title>AntiCheat Benchmark</title><style>{CSS}</style></head><body><main>",
             f"<h1>AntiCheat Benchmark – {e(meta['name'])}</h1>",
             f"<p class='sub'>Run {e(meta['run_id'])} · Minecraft {e(meta['minecraft'])} · {meta['repetitions']} repetitions · "
             f"clients: {e(', '.join(meta['clients']))}</p>"]

    parts.append("<h2>Summary</h2><div class='cards'>")
    for s in result["summaries"]:
        a = s["all"]
        parts.append(f"<div class='card'><div>{e(s['anticheat'])} <span class='chip'>vs {e(s['client'])}</span></div>"
                     f"<div class='score'>{_num(s['score'], 0)}</div><dl>"
                     f"<dt>Detection</dt><dd class='{_cls(a['detection_rate'])}'>{_pct(a['detection_rate'])}</dd>"
                     f"<dt>Default alert</dt><dd class='{_cls(a.get('default_detection_rate'))}'>{_pct(a.get('default_detection_rate'))}</dd>"
                     f"<dt>False positives</dt><dd class='{_cls(a['false_positive_rate'], False)}'>{_pct(a['false_positive_rate'])}</dd>"
                     f"<dt>Mitigation</dt><dd class='{_cls(a['mitigation'])}'>{_pct(a['mitigation'])}</dd>"
                     f"<dt>Median time to flag</dt><dd>{_num(a['median_time_to_flag_s'], 1)} s</dd>"
                     f"<dt>Valid variants</dt><dd>{s['valid_variants']}</dd></dl></div>")
    parts.append("</div>")
    weights = meta.get("scoring", {})
    parts.append(f"<p class='legend'>Score = weighted mean of detection rate, 1 − false-positive rate and mitigation "
                 f"(weights {e(', '.join(f'{k} {v}' for k, v in weights.items()))}). Only cheat variants with a measurable advantage "
                 f"in the reference run without anticheat count, plus targeted bypasses that only gain an advantage with the anticheat "
                 f"installed.</p>")

    acs = [a for a in _ac_names(result) if a != "none"]
    for client in sorted({v["client"] for v in result["variants"]}):
        parts.append(f"<h2>Cheats – {e(client)}</h2><p class='legend'>Per cell: detection rate, then retained advantage "
                     f"(how much of the cheat's effect survives the anticheat; lower is better). Raw = effect without anticheat.</p>")
        parts.append("<div class='wrap'><table><tr><th>Category</th><th>Scenario</th><th>Variant</th><th>Metric</th><th>Raw advantage</th>")
        for ac in acs:
            parts.append(f"<th>{e(ac)} detect</th><th>{e(ac)} retained</th><th>{e(ac)} checks</th>")
        parts.append("<th>Notes</th></tr>")
        keys = sorted({(v["category"], v["scenario"], v["variant"]) for v in result["variants"] if v["client"] == client})
        index = {(v["anticheat"], v["scenario"], v["variant"]): v for v in result["variants"] if v["client"] == client}
        for category, scenario, variant in keys:
            ref = index.get(("none", scenario, variant)) or next(index[k] for k in index if k[1:] == (scenario, variant))
            notes = []
            bypass_acs = [ac for ac in acs if index.get((ac, scenario, variant), {}).get("bypass_only")]
            if bypass_acs:
                notes.append(f"targeted bypass: advantage only with {', '.join(bypass_acs)}")
            elif not ref["effective"]:
                notes.append("no measurable effect without anticheat")
            for ac in acs:
                v = index.get((ac, scenario, variant))
                if v and v["setup_issues"]:
                    notes.append("setup: " + "; ".join(v["setup_issues"]))
            for ac in ["none"] + acs:
                v = index.get((ac, scenario, variant))
                if v and v["kicks"]:
                    flagged = f", flagged before kick {v['flagged_before_kick']}/{v['kicks']}" if ac != "none" else ""
                    notes.append(f"{ac}: {v['kicks']} kicked ({'; '.join(v['kick_reasons'])}){flagged}")
            parts.append(f"<tr><td>{e(category)}</td><td>{e(scenario)}</td><td>{e(variant)}</td><td>{e(ref['metric'])}</td>"
                         + _cell(_num(ref["raw_advantage"]), "" if ref["effective"] else "bad"))
            for ac in acs:
                v = index.get((ac, scenario, variant))
                if not v:
                    parts.append("<td></td><td></td><td></td>")
                    continue
                parts.append(_cell(f"{_pct(v['detection_rate'])} <span class='note'>({v['detected']}/{v['trials']})</span>", _cls(v["detection_rate"])))
                parts.append(_cell(_pct(v["retained_advantage"]), _cls(v["retained_advantage"], False)))
                parts.append("<td>" + "".join(f"<span class='chip'>{e(str(n))} ×{c}</span>" for n, c in v["top_checks"]) + "</td>")
            parts.append(f"<td class='note'>{e('; '.join(dict.fromkeys(notes)))}</td></tr>")
        parts.append("</table></div>")

    parts.append("<h2>False positives</h2><p class='legend'>Baseline trials run the same inputs with the cheat switched off. "
                 "Any flag here hits a legitimate (scripted) player.</p><div class='wrap'><table>"
                 "<tr><th>Client</th><th>AntiCheat</th><th>Scenario</th><th>Flagged trials</th><th>Checks</th></tr>")
    for b in result["baselines"]:
        if b["anticheat"] == "none":
            continue
        parts.append(f"<tr><td>{e(b['client'])}</td><td>{e(b['anticheat'])}</td><td>{e(b['scenario'])}</td>"
                     + _cell(f"{_pct(b['false_positive_rate'])} ({b['flagged']}/{b['trials']})", _cls(b["false_positive_rate"], False))
                     + "<td>" + "".join(f"<span class='chip'>{e(str(n))} ×{c}</span>" for n, c in b["top_checks"]) + "</td></tr>")
    parts.append("</table></div>")

    parts.append("<h2>Run health</h2><div class='wrap'><table><tr><th>Run</th><th>Finished</th><th>Joins</th><th>Unattributed flags</th><th>Errors</th></tr>")
    for key, info in result["runs"].items():
        errors = "; ".join(str(err.get("message", err)) for err in info["errors"][:5])
        parts.append(f"<tr><td>{e(key)}</td><td>{'yes' if info['done'] else 'no'}</td>" + _cell(str(info.get("joins", "?")))
                     + _cell(str(info["unattributed_flags"]))
                     + f"<td class='note'>{e(errors) or '–'}</td></tr>")
    parts.append("</table></div></main></body></html>")
    return "".join(parts)


def write_reports(result: dict, run_dir: Path) -> tuple[Path, Path]:
    md = run_dir / "report.md"
    page = run_dir / "report.html"
    md.write_text(markdown(result), encoding="utf-8")
    page.write_text(html_report(result), encoding="utf-8")
    return md, page
