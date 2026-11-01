"""Page images -> Khojki Unicode text (UTF-8) plus per-line JSON."""
import argparse
import json
import time
from pathlib import Path

import cv2

from khojki.normalize import normalize
from khojki.recognize import Recognizer
from khojki.score import render_score
from khojki.segment import save_overlay, segment_page
from khojki.validate import validate


def process_page(path: Path, rec: Recognizer) -> dict:
    """Run every stage on one page and return the per-line records."""
    start = time.perf_counter()
    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise SystemExit(f"cannot read {path}")
    boxes, info = segment_page(gray)
    seg_seconds = time.perf_counter() - start
    lines = []
    for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
        t = time.perf_counter()
        crop = gray[y0:y1, x0:x1]
        raw, conf = rec(crop)
        text, repairs = normalize(raw)
        lines.append({
            "line": i,
            "box": [x0, y0, x1, y1],
            "raw": raw,
            "text": text,
            "repairs": dict(repairs),
            "errors": validate(text),
            "confidence": round(conf, 4),
            "render_score": round(render_score(crop, text), 4),
            "seconds": round(time.perf_counter() - t, 3),
        })
    return {
        "page": path.name,
        "size": [gray.shape[1], gray.shape[0]],
        "skew_degrees": info["angle"],
        "text_block": list(info["block"]),
        "segment_seconds": round(seg_seconds, 3),
        "seconds": round(time.perf_counter() - start, 3),
        "lines": lines,
        "_gray": gray,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pages", nargs="+", type=Path)
    ap.add_argument("--model", default="models/khojki_best.mlmodel")
    ap.add_argument("--out", type=Path, default=Path("results/out"))
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    t = time.perf_counter()
    rec = Recognizer(a.model, a.device)
    load_seconds = time.perf_counter() - t
    timing = {"model": a.model, "device": a.device, "model_load_seconds": round(load_seconds, 2),
              "pages": {}}
    for path in a.pages:
        result = process_page(path, rec)
        gray = result.pop("_gray")
        stem = path.stem
        (a.out / f"{stem}.txt").write_text(
            "".join(line["text"] + "\n" for line in result["lines"]), encoding="utf-8")
        (a.out / f"{stem}.json").write_text(
            json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        save_overlay(gray, [tuple(line["box"]) for line in result["lines"]],
                     a.out / f"{stem}_overlay.png")
        n_err = sum(1 for line in result["lines"] if line["errors"])
        timing["pages"][stem] = {"seconds": result["seconds"], "lines": len(result["lines"])}
        print(f"{stem}: {len(result['lines'])} lines, {result['seconds']:.2f} s, "
              f"{n_err} lines with validator errors")
    (a.out / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
