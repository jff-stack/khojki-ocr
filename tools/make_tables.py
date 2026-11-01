"""Write every numeric table in README.md and RETRO.md from files in results/.

Tables live between markers such as <!-- TABLE:cer --> ... <!-- /TABLE:cer -->.
Inline values use <!-- VAL:name -->...<!-- /VAL:name -->. Missing data becomes [TODO].
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

R = Path("results")
TODO = "[TODO]"
VLM_NOT_RUN = ("Not run (no API key). GlotOCR Bench (arXiv 2604.12978) reports all 14 tested "
               "systems score 0 on Khojki; not verified here.")
EST_LINES = 1000


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []


def pct(e, n) -> str:
    return f"{e / n:.1%} ({e}/{n})" if n else TODO


def table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


ERROR_KINDS = ["orphan mark", "decomposed vowel", "out of order", "vowel signs on one letter",
               "illegal code point", "section mark", "U+FFFD", "not NFC"]


def error_kind(message: str) -> str:
    return next((k for k in ERROR_KINDS if k in message), "other")


def cp_list(text: str) -> str:
    return " ".join(f"U+{ord(c):04X}" for c in text)


def build(s: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Return (tables, inline values) keyed by marker name."""
    runs = s.get("runs", {})
    names = {"A": "auto line crop + normalize", "B": "oracle crop + normalize",
             "C": "oracle crop, raw model output"}
    synth = load_json(R / "train_summary.json")
    labels = {"damaged": "damaged"}
    if "clean" in synth and "damaged" in synth:
        labels["clean"] = (f"clean (did not converge: {synth['clean']['epochs']} epochs vs "
                           f"{synth['damaged']['epochs']})")
    t, v = {}, {}

    rows = []
    for model, by_run in runs.items():
        for run in "ABC":
            r = by_run[run]
            rows.append([labels.get(model, model), f"{run}: {names[run]}", pct(r["edits"], r["n"]),
                         pct(r["edits_nosep"], r["n_nosep"]), pct(r["edits_graph"], r["n_graph"])])
    vlm = s.get("vlm")
    if vlm:
        rows.append([f"VLM {vlm['model']}", "oracle crop, raw output", pct(vlm["edits"], vlm["n"]),
                     "", ""])
    else:
        rows.append(["VLM baseline", VLM_NOT_RUN, "", "", ""])
    t["cer"] = table(["Model", "Run", "CER (code points)", "CER without U+1123A",
                      "CER (graphemes)"], rows) if runs else TODO

    preds = s.get("predictions", {})
    rows = []
    for line_id, p in preds.items():
        e = Levenshtein.distance(p["gt"], p["B"])
        rows.append([line_id, len(p["gt"]), e, f"{e / len(p['gt']):.1%}", p["render_score"],
                     p["iou"], p["B"] or "(empty)"])
    t["lines"] = table(["Line", "N", "Edits (B)", "CER (B)", "Render score", "Auto-box IoU",
                        "Output (B)"], rows) if rows else TODO

    stages = load_csv(R / "stages.csv")
    t["stages"] = table(["Stage", "Edits", "Share"],
                        [[r["stage"].replace("_", " "), r["edits"], f"{float(r['share']):.0%}"]
                         for r in stages]) if stages else TODO

    conf = load_csv(R / "confusions.csv")
    t["confusions"] = table(["#", "Ground truth", "Predicted", "Count"],
                            [[r["rank"], r["gt_name"], r["pred_name"], r["count"]]
                             for r in conf]) if conf else TODO

    rows = []
    for p in sorted((R / "out").glob("page_*.json")):
        page = load_json(p)
        errs = Counter(error_kind(e) for ln in page["lines"] for e in ln["errors"])
        kinds = ", ".join(f"{k} ({n})" for k, n in errs.most_common()) or "none"
        rows.append([page["page"], len(page["lines"]), f"{page['seconds']:.1f}",
                     sum(1 for ln in page["lines"] if ln["errors"]), kinds])
    t["pages"] = table(["Page", "Lines found", "Seconds", "Lines with validator errors",
                        "Error kinds"], rows) if rows else TODO

    exp = load_csv(R / "experiments.csv")
    t["experiments"] = table(["Date", "Experiment", "Settings", "Metric", "Value", "Minutes"],
                             [[r["date"], r["name"], r["settings"], r["metric"], r["value"],
                               r["minutes"]] for r in exp]) if exp else TODO

    gt_rows = []
    for line_id, p in preds.items():
        gt_rows.append([f"`{line_id}`", f"![{line_id}](data/gt_lines/{line_id}.png)", p["gt"],
                        f"<sub>{cp_list(p['gt'])}</sub>"])
    t["testlines"] = table(["Line", "Scan", "Unicode", "Code points"], gt_rows) if gt_rows else TODO

    timing = s.get("timing") or {}
    pages = timing.get("pages", {})
    ld = s.get("line_detection", {})
    b = runs.get("damaged", {}).get("B")
    a = runs.get("damaged", {}).get("A")
    c = runs.get("clean", {}).get("B")
    v["cer_b"] = pct(b["edits"], b["n"]) if b else TODO
    v["cer_a"] = pct(a["edits"], a["n"]) if a else TODO
    v["cer_clean"] = pct(c["edits"], c["n"]) if c else TODO
    v["n_cp"] = str(s.get("n_codepoints", TODO))
    v["auto_lines"] = str(ld.get("auto_lines", TODO))
    v["manual_lines"] = str(ld.get("manual_lines") or TODO)
    v["matched"] = str(ld.get("gt_lines_matched", TODO))
    v["spearman"] = str(s.get("spearman_render_score_vs_cer", TODO))
    first = load_json(R / "labelling_manual.json").get("first_check")
    v["first_check_min"] = str(first["total_minutes"]) if first else TODO
    v["first_check_per_line"] = str(first["minutes_per_line"]) if first else TODO
    v["est_hours_1000"] = (str(round(EST_LINES * first["minutes_per_line"] / 60))
                           if first else TODO)
    p18 = pages.get("page_18")
    v["sec_per_page"] = f"{p18['seconds']:.1f}" if p18 else TODO
    v["device"] = timing.get("device", TODO)
    for k in ("damaged", "clean"):
        info = synth.get(k)
        v[f"val_cer_{k}"] = f"{info['val_cer']:.1%}" if info and info.get("val_cer") is not None else TODO
        v[f"train_min_{k}"] = str(info["minutes"]) if info else TODO
        v[f"epochs_{k}"] = str(info["epochs"]) if info else TODO
    gates = {r["name"]: r["value"] for r in exp if r["name"].startswith("gate_")}
    v["gate_on_damaged"] = f"{gates['gate_khojki_best_on_damaged']}%" if "gate_khojki_best_on_damaged" in gates else TODO
    v["gate_on_clean"] = f"{gates['gate_khojki_best_on_clean']}%" if "gate_khojki_best_on_clean" in gates else TODO
    draft = load_json(R / "gt_draft_check.json")
    v["draft_cer"] = pct(draft["edits"], draft["n"]) if draft else TODO
    v["draft_lines_changed"] = f"{draft['lines_changed']} of {len(draft['lines'])}" if draft else TODO
    cs = load_json(R / "corpus_stats.json")
    v["corpus_lines"] = str(cs.get("total", TODO))
    v["corpus_cov"] = f"{cs['coverage_pct']}%" if cs else TODO
    v["vlm_cer"] = pct(vlm["edits"], vlm["n"]) if vlm else VLM_NOT_RUN
    stage_map = {r["stage"]: r for r in stages}
    for k in ("line_detection", "recognition", "mapping"):
        r = stage_map.get(k)
        v[f"stage_{k}"] = f"{r['edits']} ({float(r['share']):.0%})" if r else TODO
    return t, v


def fill(path: Path, tables: dict[str, str], values: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for name, body in tables.items():
        text = re.sub(rf"(<!-- TABLE:{name} -->).*?(<!-- /TABLE:{name} -->)",
                      lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text, flags=re.S)
    for name, val in values.items():
        text = re.sub(rf"(<!-- VAL:{name} -->).*?(<!-- /VAL:{name} -->)",
                      lambda m: f"{m.group(1)}{val}{m.group(2)}", text, flags=re.S)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    tables, values = build(load_json(R / "summary.json"))
    for doc in ("README.md", "RETRO.md"):
        if Path(doc).exists():
            fill(Path(doc), tables, values)
            left = re.findall(r"<!-- (?:TABLE|VAL):(\w+) -->\s*\[TODO\]", Path(doc).read_text(encoding="utf-8"))
            print(f"{doc}: filled, [TODO] left for: {', '.join(left) or 'none'}")


if __name__ == "__main__":
    main()
