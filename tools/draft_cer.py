"""Compare the AI-drafted ground truth with the human-checked version.

Writes results/gt_draft_check.json.
"""
import json
from pathlib import Path

from rapidfuzz.distance import Levenshtein

DRAFT = Path("data/gt_draft")
GT = Path("data/gt_lines")
OUT = Path("results/gt_draft_check.json")


def main() -> None:
    lines = {}
    for f in sorted(GT.glob("*.gt.txt")):
        gt = f.read_text(encoding="utf-8").strip()
        draft = (DRAFT / f.name).read_text(encoding="utf-8").strip()
        lines[f.name.split(".")[0]] = {"n": len(gt), "edits": Levenshtein.distance(draft, gt)}
    edits = sum(v["edits"] for v in lines.values())
    n = sum(v["n"] for v in lines.values())
    out = {"lines": lines, "edits": edits, "n": n, "cer": round(edits / n, 4),
           "lines_changed": sum(v["edits"] > 0 for v in lines.values())}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"draft vs checked: {edits}/{n} = {edits / n:.1%}, {out['lines_changed']} lines changed")


if __name__ == "__main__":
    main()
