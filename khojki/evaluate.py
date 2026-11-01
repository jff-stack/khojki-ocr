"""Evaluate on the ground-truth lines: CER, stage attribution and confusions."""
import argparse
import csv
import json
import unicodedata as ud
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import regex
from PIL import Image, ImageDraw, ImageFont
from rapidfuzz.distance import Levenshtein

from khojki.charset import MARKS, WORD_SEPARATOR
from khojki.normalize import normalize
from khojki.score import FONT, render_score
from khojki.segment import segment

SEP = chr(WORD_SEPARATOR)
GT_DIR = Path("data/gt_lines")
RESULTS = Path("results")
PAGE = Path("data/pages/page_18.png")
PAGE_DPI = 300
ORACLE_DPI = 400


def cer(ref: str, hyp: str, unit: str = "cp", drop_sep: bool = False) -> tuple[int, int]:
    """Return (edits, N) on NFC code points ('cp') or extended graphemes ('grapheme')."""
    ref, hyp = ud.normalize("NFC", ref), ud.normalize("NFC", hyp)
    if drop_sep:
        ref, hyp = ref.replace(SEP, ""), hyp.replace(SEP, "")
    if unit == "grapheme":
        r, h = regex.findall(r"\X", ref), regex.findall(r"\X", hyp)
        ids = {g: i for i, g in enumerate(dict.fromkeys(r + h))}
        return Levenshtein.distance([ids[g] for g in r], [ids[g] for g in h]), len(r)
    return Levenshtein.distance(ref, hyp), len(ref)


def edit_pairs(ref: str, hyp: str) -> list[tuple[str, str]]:
    """(ref_char, hyp_char) for every edit; '' marks the empty side of an insert or delete."""
    pairs = []
    for op in Levenshtein.editops(ref, hyp):
        if op.tag == "replace":
            pairs.append((ref[op.src_pos], hyp[op.dest_pos]))
        elif op.tag == "delete":
            pairs.append((ref[op.src_pos], ""))
        else:
            pairs.append(("", hyp[op.dest_pos]))
    return pairs


_font = None


def _glyph(ch: str) -> np.ndarray:
    """Render one character (marks on a KA base) as a binary image."""
    global _font
    if _font is None:
        _font = ImageFont.truetype(FONT, 64, layout_engine=ImageFont.Layout.RAQM)
    text = ("\U00011208" + ch) if ord(ch) in MARKS else ch
    img = Image.new("L", (200, 120), 255)
    ImageDraw.Draw(img).text((20, 20), text, font=_font, fill=0)
    return np.asarray(img) < 128


def same_glyph(a: str, b: str) -> bool:
    """True if two different code points draw identically in the font (a mapping error)."""
    return bool(a and b and a != b and np.array_equal(_glyph(a), _glyph(b)))


def spearman(x: list[float], y: list[float]) -> float | None:
    """Spearman rank correlation with average ranks for ties."""
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None

    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=v.__getitem__)
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    var = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return cov / var if var else None


def iou(a: tuple, b: tuple) -> float:
    """Intersection over union of two (x0, y0, x1, y1) boxes."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def load_gt() -> list[dict]:
    """GT lines with text and oracle box scaled to the pipeline DPI."""
    check = json.loads((RESULTS / "oracle_check.json").read_text(encoding="utf-8"))
    f = PAGE_DPI / ORACLE_DPI
    lines = []
    for line_id, info in check.items():
        text = (GT_DIR / f"{line_id}.gt.txt").read_text(encoding="utf-8").strip()
        box = tuple(round(v * f) for v in info["crop_box"])
        lines.append({"id": line_id, "text": text, "box": box})
    return lines


def run_model(model_path: str, gray: np.ndarray, gt: list[dict], auto: list[tuple]) -> dict:
    """Runs A (auto crop), B (oracle crop, normalized) and C (oracle crop, raw)."""
    from khojki.recognize import Recognizer

    rec = Recognizer(model_path)
    out = {}
    for line in gt:
        ob = line["box"]
        crop = gray[ob[1]:ob[3], ob[0]:ob[2]]
        raw, _ = rec(crop)
        normed, repairs = normalize(raw)
        best = max(auto, key=lambda b: iou(b, ob), default=None)
        best_iou = iou(best, ob) if best else 0.0
        if best and best_iou >= 0.5:
            auto_crop = gray[best[1]:best[3], best[0]:best[2]]
            auto_text, _ = normalize(rec(auto_crop)[0])
        else:
            auto_text = ""
        out[line["id"]] = {"A": auto_text, "B": normed, "C": raw, "repairs": dict(repairs),
                           "auto_box": list(best) if best else None, "iou": round(best_iou, 3),
                           "render_score": round(render_score(crop, normed), 4)}
    return out


def score_runs(gt: list[dict], preds: dict, model: str) -> list[dict]:
    """One CSV row per (model, run, line)."""
    rows = []
    for line in gt:
        for run in "ABC":
            hyp = preds[line["id"]][run]
            e, n = cer(line["text"], hyp)
            e_ns, n_ns = cer(line["text"], hyp, drop_sep=True)
            e_g, n_g = cer(line["text"], hyp, unit="grapheme")
            rows.append({"model": model, "run": run, "id": line["id"], "edits": e, "n": n,
                         "edits_nosep": e_ns, "n_nosep": n_ns, "edits_graph": e_g, "n_graph": n_g,
                         "hyp": hyp})
    return rows


def total(rows: list[dict], model: str, run: str, key: str = "") -> tuple[int, int]:
    """Summed (edits, N) for one model and run."""
    sel = [r for r in rows if r["model"] == model and r["run"] == run]
    sfx = f"_{key}" if key else ""
    return sum(r[f"edits{sfx}"] for r in sel), sum(r[f"n{sfx}"] for r in sel)


def vlm_scores(gt: list[dict]) -> dict | None:
    """CER of raw VLM output, if the baseline was run."""
    raw_dir = RESULTS / "vlm_raw"
    if not (raw_dir / "summary.json").exists():
        return None
    edits = n = 0
    for line in gt:
        p = raw_dir / f"{line['id']}.txt"
        hyp = p.read_text(encoding="utf-8").strip() if p.exists() else ""
        e, k = cer(line["text"], hyp)
        edits, n = edits + e, n + k
    summary = json.loads((raw_dir / "summary.json").read_text(encoding="utf-8"))
    return {"edits": edits, "n": n, "cer": round(edits / n, 4), **summary}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="models/khojki_best.mlmodel")
    ap.add_argument("--clean-model", default="models/khojki_clean.mlmodel")
    a = ap.parse_args()

    gray = cv2.imread(str(PAGE), cv2.IMREAD_GRAYSCALE)
    gt = load_gt()
    auto = segment(gray)

    models = {"damaged": a.model}
    if Path(a.clean_model).exists():
        models["clean"] = a.clean_model
    preds = {name: run_model(path, gray, gt, auto) for name, path in models.items()}
    rows = [r for name in models for r in score_runs(gt, preds[name], name)]
    write_csv(RESULTS / "cer.csv", rows)

    best = preds["damaged"]
    eA, n = total(rows, "damaged", "A")
    eB, _ = total(rows, "damaged", "B")
    eC, _ = total(rows, "damaged", "C")
    pairs_b = [p for line in gt for p in edit_pairs(line["text"], best[line["id"]]["B"])]
    same = sum(1 for a_, b_ in pairs_b if same_glyph(a_, b_))
    stages = {"line_detection": eA - eB, "mapping": (eC - eB) + same, "recognition": eB - same}
    denom = sum(max(0, v) for v in stages.values())
    write_csv(RESULTS / "stages.csv", [
        {"stage": k, "edits": v, "share": round(max(0, v) / denom, 4) if denom else 0}
        for k, v in stages.items()])

    def label(ch: str) -> str:
        return f"U+{ord(ch):04X} {ud.name(ch, '?')}" if ch else "(none)"

    conf = Counter(pairs_b).most_common(10)
    write_csv(RESULTS / "confusions.csv", [
        {"rank": i, "gt": g, "pred": p, "gt_name": label(g), "pred_name": label(p), "count": c}
        for i, ((g, p), c) in enumerate(conf, 1)])

    line_cer = {line["id"]: cer(line["text"], best[line["id"]]["B"]) for line in gt}
    scores = [best[k]["render_score"] for k in line_cer]
    rho = spearman(scores, [e / n_ for e, n_ in line_cer.values()])

    counts_path = GT_DIR / "page_counts.json"
    manual = json.loads(counts_path.read_text())["page_18"] if counts_path.exists() else None
    timing_path = RESULTS / "out" / "timing.json"
    timing = json.loads(timing_path.read_text()) if timing_path.exists() else None

    def run_summary(model: str, run: str) -> dict:
        e, k = total(rows, model, run)
        e_ns, k_ns = total(rows, model, run, "nosep")
        e_g, k_g = total(rows, model, run, "graph")
        return {"edits": e, "n": k, "cer": round(e / k, 4),
                "edits_nosep": e_ns, "n_nosep": k_ns, "cer_nosep": round(e_ns / k_ns, 4),
                "edits_graph": e_g, "n_graph": k_g, "cer_graph": round(e_g / k_g, 4)}

    summary = {
        "n_lines": len(gt),
        "n_codepoints": n,
        "runs": {m: {r: run_summary(m, r) for r in "ABC"} for m in models},
        "stages": stages,
        "same_glyph_edits_in_B": same,
        "repairs_B": dict(sum((Counter(best[k]["repairs"]) for k in best), Counter())),
        "line_detection": {"page": PAGE.name, "auto_lines": len(auto), "manual_lines": manual,
                           "gt_lines_matched": sum(1 for k in best if best[k]["iou"] >= 0.5),
                           "ious": {k: best[k]["iou"] for k in best}},
        "spearman_render_score_vs_cer": round(rho, 3) if rho is not None else None,
        "render_scores": {k: best[k]["render_score"] for k in best},
        "vlm": vlm_scores(gt),
        "timing": timing,
        "predictions": {k: {**best[k], "gt": line["text"]} for k, line in zip(best, gt)},
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False),
                                          encoding="utf-8")
    b = summary["runs"]["damaged"]["B"]
    print(f"CER (oracle crops, damaged model): {b['edits']}/{b['n']} = {b['edits'] / b['n']:.1%}")
    print(f"stages: {stages}")


if __name__ == "__main__":
    main()
