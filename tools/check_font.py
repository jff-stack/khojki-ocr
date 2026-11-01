"""Report which assigned Khojki and Gujarati-digit code points the font covers."""
import argparse
import unicodedata as ud
from pathlib import Path

from fontTools.ttLib import TTFont

RANGES = [(0x11200, 0x11241), (0x0AE6, 0x0AEF)]


def coverage(font_path: str) -> list[tuple[int, str, bool]]:
    """Return (code point, name, has_glyph) for every assigned code point in RANGES."""
    cmap = TTFont(font_path).getBestCmap()
    rows = []
    for lo, hi in RANGES:
        for cp in range(lo, hi + 1):
            name = ud.name(chr(cp), "")
            if name:
                rows.append((cp, name, cp in cmap))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--font", default="tools/NotoSansKhojki-Regular.ttf")
    ap.add_argument("--out", default="results/font_coverage.txt")
    a = ap.parse_args()

    rows = coverage(a.font)
    version = TTFont(a.font)["name"].getDebugName(5)
    missing = [r for r in rows if not r[2]]
    lines = [
        f"font: {a.font} ({version})",
        f"unicodedata version: {ud.unidata_version}",
        f"assigned code points checked: {len(rows)}",
        f"missing glyphs: {len(missing)}",
        "",
    ]
    lines += [f"U+{cp:04X}  {'ok     ' if ok else 'MISSING'}  {name}" for cp, name, ok in rows]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4]))
    for cp, name, _ in missing:
        print(f"  missing U+{cp:04X} {name}")


if __name__ == "__main__":
    main()
