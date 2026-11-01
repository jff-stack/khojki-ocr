"""Summarise ketos training runs from checkpoint names and logs.

Writes results/train_summary.json. kraken names checkpoints checkpoint_<epoch>-<val_accuracy>.ckpt.
"""
import json
import re
from pathlib import Path

RUNS = Path("models/runs")
OUT = Path("results/train_summary.json")


def summarise(name: str) -> dict | None:
    ckpts = [(int(m[1]), float(m[2]), p) for p in (RUNS / name).glob("checkpoint_*-*.ckpt")
             if (m := re.match(r"checkpoint_(\d+)-([\d.]+)\.ckpt", p.name))]
    if not ckpts:
        return None
    epoch, acc, path = max(ckpts, key=lambda c: (c[1], -c[0]))
    log = Path(f"results/train_{name}.log").read_text(encoding="utf-8", errors="replace")
    minutes = re.findall(r"train_minutes=(\d+)", log)
    return {"best_epoch": epoch, "best_checkpoint": path.as_posix(), "val_accuracy": acc,
            "val_cer": round(1 - acc, 4), "epochs": max(c[0] for c in ckpts) + 1,
            "minutes": int(minutes[-1]) if minutes else None,
            "early_stopped": "Converting best model" in log}


def main() -> None:
    out = {n: s for n in ("damaged", "clean") if (s := summarise(n))}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
