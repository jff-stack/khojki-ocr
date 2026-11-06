"""Write every number in docs/architecture.html from files in results/.

Uses the same markers as make_tables.py: <!-- VAL:name -->...<!-- /VAL:name --> for inline
values and <!-- TABLE:name -->...<!-- /TABLE:name --> for blocks. Missing data becomes [TODO].
Exits 1 if any marker is left as [TODO] or has no value.
"""
import html
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

from make_tables import R, TODO, error_kind, fill, load_csv, load_json, pct

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from khojki.validate import validate  # noqa: E402

PAGE = Path("docs/architecture.html")
FLOW_LINE = "p18_l02"


def rate(e, n) -> str:
    return f"{e / n:.1%}" if n else TODO


def esc(x) -> str:
    return html.escape(str(x))


def cp_head(text: str, k: int = 6) -> str:
    head = " ".join(f"U+{ord(c):04X}" for c in text[:k])
    return head + (" …" if len(text) > k else "")


def bar_path(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    """Bar with rounded top corners, anchored to the baseline."""
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{y + h:.1f}V{y + r:.1f}Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f}"
            f"H{x + w - r:.1f}Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}V{y + h:.1f}Z")


def line_bars(rows: list[dict]) -> str:
    """Grouped SVG bars of per-line CER for runs A and B of the damaged model."""
    sel = {(r["run"], r["id"]): (int(r["edits"]), int(r["n"])) for r in rows
           if r["model"] == "damaged" and r["run"] in "AB"}
    ids = sorted({i for _, i in sel})
    if not ids:
        return TODO
    w, h, left, right, top, bottom = 640, 240, 48, 12, 14, 34
    pw, ph = w - left - right, h - top - bottom
    peak = max(e / n for e, n in sel.values())
    ymax = max(0.1, math.ceil(peak * 10) / 10)
    y = lambda v: top + ph * (1 - v / ymax)  # noqa: E731
    out = [f'<svg class="bars" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="Per-line CER for runs A and B, damaged model">']
    steps = round(ymax / 0.1)
    for i in range(steps + 1):
        v = ymax * i / steps
        cls = "base" if i == 0 else "grid"
        out.append(f'<line class="{cls}" x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        out.append(f'<text class="tick" x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:.0%}</text>')
    group = pw / len(ids)
    bw = min(28.0, group * 0.3)
    for gi, line_id in enumerate(ids):
        cx = left + group * (gi + 0.5)
        for ri, run in enumerate("AB"):
            if (run, line_id) not in sel:
                continue
            e, n = sel[(run, line_id)]
            x = cx - bw - 1 if ri == 0 else cx + 1
            v = e / n
            if v > 0:
                out.append(f'<path class="s-{run.lower()}" d="{bar_path(x, y(v), bw, y(0) - y(v))}"/>')
            tip = f"{line_id} · run {run} · {v:.1%} ({e}/{n})"
            out.append(f'<rect class="hit" x="{x - 1:.1f}" y="{top}" width="{bw + 2:.1f}" height="{ph}" '
                       f'tabindex="0" data-tip="{esc(tip)}" aria-label="{esc(tip)}"/>')
        out.append(f'<text class="xlabel" x="{cx:.1f}" y="{h - 12}" text-anchor="middle">{esc(line_id)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def line_table(rows: list[dict]) -> str:
    sel = {(r["run"], r["id"]): (int(r["edits"]), int(r["n"])) for r in rows if r["model"] == "damaged"}
    ids = sorted({i for _, i in sel})
    if not ids:
        return TODO
    body = ["<table><thead><tr><th>Line</th><th>Run A</th><th>Run B</th><th>Run C</th></tr></thead><tbody>"]
    for line_id in ids:
        cells = "".join(f"<td>{pct(*sel[(r, line_id)]) if (r, line_id) in sel else ''}</td>" for r in "ABC")
        body.append(f"<tr><td>{esc(line_id)}</td>{cells}</tr>")
    body.append("</tbody></table>")
    return "\n".join(body)


def stage_rows(stages: list[dict]) -> str:
    if not stages:
        return TODO
    out = []
    for r in stages:
        share = float(r["share"])
        out.append(f'<div class="stage-row"><span class="stage-name">{esc(r["stage"].replace("_", " "))}</span>'
                   f'<span class="meter"><span style="width:{share:.0%}"></span></span>'
                   f'<span class="stage-val">{esc(r["edits"])} edits · {share:.0%}</span></div>')
    return "\n".join(out)


def page_table(timing: dict) -> str:
    pages = timing.get("pages", {})
    if not pages:
        return TODO
    body = ["<table><thead><tr><th>Page</th><th>Lines found</th><th>Seconds</th>"
            "<th>Lines with validator errors</th><th>Error kinds</th></tr></thead><tbody>"]
    for stem in sorted(pages):
        rec = load_json(R / "out" / f"{stem}.json")
        lines = rec.get("lines", [])
        errs = Counter(error_kind(e) for ln in lines for e in ln["errors"])
        kinds = ", ".join(f"{k} ({n})" for k, n in errs.most_common()) or "none"
        bad = sum(1 for ln in lines if ln["errors"]) if rec else TODO
        body.append(f"<tr><td>{esc(stem)}</td><td>{pages[stem]['lines']}</td>"
                    f"<td>{pages[stem]['seconds']:.1f}</td><td>{bad}</td><td>{esc(kinds)}</td></tr>")
    body.append("</tbody></table>")
    return "\n".join(body)


def build() -> tuple[dict[str, str], dict[str, str]]:
    """Return (blocks, inline values) keyed by marker name."""
    s = load_json(R / "summary.json")
    rows = load_csv(R / "cer.csv")
    stages = load_csv(R / "stages.csv")
    train = load_json(R / "train_summary.json")
    timing = load_json(R / "out" / "timing.json")
    corpus = load_json(R / "corpus_stats.json")
    exp = {r["name"]: r["value"] for r in load_csv(R / "experiments.csv")}
    t, v = {}, {}

    t["linebars"] = line_bars(rows)
    t["linetable"] = line_table(rows)
    t["stages"] = stage_rows(stages)
    t["pages"] = page_table(timing)

    v["n_lines"] = str(s.get("n_lines", TODO))
    v["n_cp"] = str(s.get("n_codepoints", TODO))
    runs = s.get("runs", {})
    dmg = runs.get("damaged", {})
    for run in "ABC":
        r = dmg.get(run)
        v[f"cer_{run.lower()}"] = rate(r["edits"], r["n"]) if r else TODO
        v[f"cer_{run.lower()}_frac"] = f"{r['edits']}/{r['n']}" if r else TODO
    b = dmg.get("B")
    v["cer_b_nosep"] = pct(b["edits_nosep"], b["n_nosep"]) if b else TODO
    v["cer_b_graph"] = pct(b["edits_graph"], b["n_graph"]) if b else TODO
    cb = runs.get("clean", {}).get("B")
    v["cer_clean_b"] = pct(cb["edits"], cb["n"]) if cb else TODO

    smap = {r["stage"]: r for r in stages}
    for k in ("line_detection", "mapping", "recognition"):
        r = smap.get(k)
        v[f"stage_{k}"] = r["edits"] if r else TODO
        v[f"share_{k}"] = f"{float(r['share']):.0%}" if r else TODO
    if "line_detection" in smap:
        ld = int(smap["line_detection"]["edits"])
        v["ld_sentence"] = (f"the automatic crops gave {-ld} fewer edits than the hand crops" if ld < 0 else
                            f"the automatic crops added {ld} edits" if ld > 0 else
                            "the automatic crops gave the same edits as the hand crops")
    else:
        v["ld_sentence"] = TODO
    v["same_glyph"] = str(s.get("same_glyph_edits_in_B", TODO))
    v["repairs_b"] = str(sum(s["repairs_B"].values())) if "repairs_B" in s else TODO

    for k in ("damaged", "clean"):
        info = train.get(k)
        v[f"val_cer_{k}"] = f"{info['val_cer']:.1%}" if info else TODO
        v[f"epochs_{k}"] = str(info["epochs"]) if info else TODO
        v[f"train_min_{k}"] = str(info["minutes"]) if info and info.get("minutes") is not None else TODO
    d = train.get("damaged")
    v["best_epoch_damaged"] = str(d["best_epoch"]) if d else TODO
    if d and b and d["val_cer"]:
        real = b["edits"] / b["n"]
        v["gap_points"] = f"{100 * (real - d['val_cer']):.1f}"
        v["gap_ratio"] = f"{real / d['val_cer']:.0f}"
    else:
        v["gap_points"] = v["gap_ratio"] = TODO

    ld = s.get("line_detection", {})
    v["auto_lines"] = str(ld.get("auto_lines", TODO))
    v["manual_lines"] = str(ld.get("manual_lines") or TODO)
    v["matched"] = str(ld.get("gt_lines_matched", TODO))
    ious = list(ld.get("ious", {}).values())
    v["iou_min"] = f"{min(ious):.2f}" if ious else TODO
    v["iou_max"] = f"{max(ious):.2f}" if ious else TODO

    rho = s.get("spearman_render_score_vs_cer")
    v["spearman"] = str(rho) if rho is not None else TODO
    v["spearman_sentence"] = (TODO if rho is None else
                              "The sign is negative: lines whose render matched worse had fewer errors, "
                              "the opposite of what a confidence signal should show." if rho < 0 else
                              "The sign is positive, as a confidence signal should be.")
    rs = list(s.get("render_scores", {}).values())
    v["rs_min"] = f"{min(rs):.2f}" if rs else TODO
    v["rs_max"] = f"{max(rs):.2f}" if rs else TODO

    v["device"] = timing.get("device", TODO)
    v["model_load_s"] = f"{timing['model_load_seconds']:.1f}" if "model_load_seconds" in timing else TODO
    page = Path(ld.get("page", "")).stem
    p = timing.get("pages", {}).get(page)
    v["flow_page"] = page or TODO
    v["sec_page"] = f"{p['seconds']:.1f}" if p else TODO
    v["lines_page"] = str(p["lines"]) if p else TODO
    v["n_pages_run"] = str(len(timing.get("pages", {}))) if timing else TODO

    v["corpus_lines"] = str(corpus.get("total", TODO))
    v["corpus_cov"] = f"{corpus['coverage_pct']}%" if "coverage_pct" in corpus else TODO
    v["synth_damaged_n"] = exp.get("render_damaged", TODO)
    v["synth_clean_n"] = exp.get("render_clean", TODO)
    for key, name in (("gate_on_damaged", "gate_khojki_best_on_damaged"),
                      ("gate_on_clean", "gate_khojki_best_on_clean"),
                      ("gate_clean_on_clean", "gate_khojki_clean_on_clean")):
        v[key] = f"{exp[name]}%" if name in exp else TODO

    line = s.get("predictions", {}).get(FLOW_LINE)
    if line:
        errors = validate(line["B"])
        v["flow_line"] = FLOW_LINE
        v["flow_raw"] = f'<span class="kh">{esc(line["C"])}</span> <code>{esc(cp_head(line["C"]))}</code>'
        v["flow_norm"] = f'<span class="kh">{esc(line["B"])}</span> <code>{esc(cp_head(line["B"]))}</code>'
        v["flow_repairs"] = str(sum(line["repairs"].values()))
        v["flow_errors"] = (f"{len(errors)} error(s), first: {esc(errors[0])}" if errors
                            else "an empty list (no rule broken)")
        v["flow_score"] = str(line["render_score"])
        record = {"text": line["B"], "repairs": line["repairs"], "errors": errors,
                  "render_score": line["render_score"]}
        v["flow_json"] = f"<code>{esc(json.dumps(record, ensure_ascii=False))}</code>"
    else:
        for k in ("flow_line", "flow_raw", "flow_norm", "flow_repairs", "flow_errors", "flow_score",
                  "flow_json"):
            v[k] = TODO
    return t, v


def main() -> None:
    if not PAGE.exists():
        raise SystemExit(f"{PAGE} not found")
    tables, values = build()
    fill(PAGE, tables, values)
    text = PAGE.read_text(encoding="utf-8")
    names = set(re.findall(r"<!-- (?:TABLE|VAL):(\w+) -->", text))
    unknown = sorted(names - set(tables) - set(values))
    left = sorted(set(re.findall(r"<!-- (?:TABLE|VAL):(\w+) -->\s*\[TODO\]", text)))
    print(f"{PAGE}: {len(names)} markers, [TODO] left for: {', '.join(left) or 'none'}, "
          f"no value for: {', '.join(unknown) or 'none'}")
    raise SystemExit(1 if left or unknown else 0)


if __name__ == "__main__":
    main()
