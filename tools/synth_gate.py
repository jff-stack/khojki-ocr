"""Run ketos test on the last N synthetic lines of a set and log the character accuracy.

usage: python tools/synth_gate.py MODEL DATA_DIR [N]
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from khojki import log_experiment  # noqa: E402

KETOS = Path(sys.executable).with_name("ketos")


def main() -> None:
    model, data = sys.argv[1], Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    with tempfile.TemporaryDirectory() as tmp:
        for png in sorted(data.glob("*.png"))[-n:]:
            shutil.copy(png, tmp)
            shutil.copy(png.with_suffix(".gt.txt"), tmp)
        out = subprocess.run([str(KETOS), "-d", "cpu", "test", "-f", "path", "-m", model,
                              *map(str, Path(tmp).glob("*.png"))],
                             capture_output=True, text=True).stdout
    acc = float(re.search(r"(-?[\d.]+)%\s+Character Accuracy\n", out)[1])
    log_experiment(f"gate_{Path(model).stem}_on_{data.name}", f"last {n} lines, ketos test",
                   "char_accuracy_pct", acc, 0)
    print(f"{model} on {data}: {acc}% character accuracy")


if __name__ == "__main__":
    main()
