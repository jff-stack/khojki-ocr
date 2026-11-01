"""Mini OCR pipeline for the Khojki script."""
import csv
import datetime as dt
from pathlib import Path

EXPERIMENTS = Path("results/experiments.csv")
FIELDS = ["date", "name", "settings", "metric", "value", "minutes"]


def log_experiment(name: str, settings: str, metric: str, value, minutes: float) -> None:
    """Append one row to results/experiments.csv."""
    EXPERIMENTS.parent.mkdir(parents=True, exist_ok=True)
    new = not EXPERIMENTS.exists()
    with EXPERIMENTS.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        w.writerow([dt.date.today().isoformat(), name, settings, metric, value, round(minutes, 2)])
