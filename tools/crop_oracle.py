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

    page = np.asarray(Image.open(a.page).convert("L"), float)
    report = {}
    ok = True
    for line_id, box in ORACLE_BOXES.items():
        ref = np.asarray(Image.open(Path(a.gt) / f"{line_id}.png").convert("L"), float)
        x0, y0 = box[0], box[1]
        rh, rw = ref.shape
        brief_size = (box[2] - box[0], box[3] - box[1])
        diff, x0, y0 = min(
            (float(np.abs(page[y:y + rh, x:x + rw] - ref).mean()), x, y)
            for x in range(x0 - 4, x0 + 5) for y in range(y0 - 4, y0 + 5))
        found = (x0, y0, x0 + rw, y0 + rh)
        passed = diff <= a.tolerance
        ok &= passed
        report[line_id] = {"brief_box": box, "crop_box": found, "brief_size": brief_size,
                           "png_size": [rw, rh], "mean_abs_diff": round(diff, 3), "pass": passed}
        note = "" if brief_size == (rw, rh) else f" (brief box is {brief_size[0]}x{brief_size[1]})"
        print(f"{line_id}: crop {found}, diff {diff:.3f} {'ok' if passed else 'FAIL'}{note}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
