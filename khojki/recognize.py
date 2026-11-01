"""Thin wrapper around a kraken recognition model for single line crops."""
import numpy as np
from PIL import Image


class Recognizer:
    """Load a kraken model once and transcribe line images."""

    def __init__(self, model_path: str, device: str = "cpu"):
        from kraken.lib import models
        self.net = models.load_any(model_path, device=device)

    def __call__(self, line: np.ndarray | Image.Image) -> tuple[str, float]:
        """Return (text, mean character confidence) for one line image."""
        from kraken import rpred
        from kraken.containers import BBoxLine, Segmentation

        im = line if isinstance(line, Image.Image) else Image.fromarray(line)
        im = im.convert("L")
        seg = Segmentation(type="bbox", imagename="line", text_direction="horizontal-lr",
                           script_detection=False,
                           lines=[BBoxLine(id="0", bbox=(0, 0, im.width, im.height))])
        record = next(iter(rpred.rpred(self.net, im, seg)))
        conf = float(np.mean(record.confidences)) if record.confidences else 0.0
        return record.prediction, conf
