"""Time the human check of one ground-truth line and append the result to timing.csv."""
import argparse
import csv
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

GT_DIR = Path("data/gt_lines")


def open_image(path: Path) -> None:
    """Open an image in the default viewer on Windows, WSL, macOS or Linux."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif "microsoft" in platform.release().lower():
        win = subprocess.run(["wslpath", "-w", str(path.resolve())], capture_output=True, text=True)
        subprocess.Popen(["explorer.exe", win.stdout.strip()])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("line_id", help="e.g. p18_l02")
    ap.add_argument("--no-open", action="store_true", help="do not open the check image")
    a = ap.parse_args()

    gt = GT_DIR / f"{a.line_id}.gt.txt"
    check = GT_DIR / f"{a.line_id}.check.png"
    if not gt.exists():
        sys.exit(f"no such line: {gt}")
    before = gt.read_text(encoding="utf-8")
    if not a.no_open:
        open_image(check)

    start = time.monotonic()
    input(f"[{a.line_id}] checking... press Enter when the line is verified or fixed ")
    seconds = round(time.monotonic() - start, 1)

    after = gt.read_text(encoding="utf-8")
    changed = "y" if after != before else "n"
    n_cp = len(after.strip())
    timing = GT_DIR / "timing.csv"
    new = not timing.exists()
    with timing.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["id", "seconds", "n_codepoints", "changed"])
        w.writerow([a.line_id, seconds, n_cp, changed])
    print(f"{a.line_id}: {seconds}s, {n_cp} code points, changed={changed}")


if __name__ == "__main__":
    main()
