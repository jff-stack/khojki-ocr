"""Re-crop the oracle line boxes from page 18 and compare them with the provided crops."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ORACLE_DPI = 400
ORACLE_BOXES = {
    "p18_l02": (418, 801, 3979, 1095),
    "p18_l03": (418, 1152, 3979, 1417),
    "p18_l04": (418, 1490, 3979, 1789),
    "p18_l05": (418, 1824, 3979, 2141),
    "p18_l06": (418, 2173, 3979, 2423),
}


def scaled_boxes(dpi: int) -> dict[str, tuple[int, int, int, int]]:
    """Oracle boxes scaled from 400 DPI to the given DPI."""
    f = dpi / ORACLE_DPI
    return {k: tuple(round(v * f) for v in box) for k, box in ORACLE_BOXES.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--page", default="data/pages/page_18_400dpi.png")
    ap.add_argument("--gt", default="data/gt_lines")
    ap.add_argument("--out", default="results/oracle_check.json")
    ap.add_argument("--tolerance", type=float, default=3.0, help="max mean abs diff (0-255)")
    a = ap.parse_args()

    page = Image.open(a.page).convert("L")
    report = {}
    ok = True
    for line_id, box in ORACLE_BOXES.items():
        crop = page.crop(box)
        ref = Image.open(Path(a.gt) / f"{line_id}.png").convert("L")
        if crop.size != ref.size:
            crop = crop.resize(ref.size, Image.BILINEAR)
        diff = float(np.abs(np.asarray(crop, float) - np.asarray(ref, float)).mean())
        passed = diff <= a.tolerance
        ok &= passed
        report[line_id] = {"box": box, "crop_size": list(ref.size), "mean_abs_diff": round(diff, 3),
                           "pass": passed}
        print(f"{line_id}: size {ref.size}, mean abs diff {diff:.3f} {'ok' if passed else 'FAIL'}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
