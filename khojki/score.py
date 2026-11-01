"""Render-and-compare confidence: 1 - IoU between the scan crop and the rendered text."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "tools/NotoSansKhojki-Regular.ttf"


def _ink(gray: np.ndarray) -> np.ndarray:
    """Otsu-binarize and crop to the ink bounding box; True = ink."""
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ys, xs = np.nonzero(bw)
    if len(ys) == 0:
        return np.zeros((1, 1), bool)
    return bw[ys.min():ys.max() + 1, xs.min():xs.max() + 1] > 0


def render_text(text: str, height: int) -> np.ndarray:
    """Render text in Noto Sans Khojki with ink roughly as tall as the crop's ink."""
    font = ImageFont.truetype(FONT, max(8, int(height * 0.9)), layout_engine=ImageFont.Layout.RAQM)
    x0, y0, x1, y1 = font.getbbox(text)
    img = Image.new("L", (max(1, x1 - x0) + 20, max(1, y1 - y0) + 20), 255)
    ImageDraw.Draw(img).text((10 - x0, 10 - y0), text, font=font, fill=0)
    return np.asarray(img)


def render_score(crop: np.ndarray, text: str) -> float:
    """0 means the rendered text overlaps the scan ink perfectly, 1 means no overlap."""
    if not text.strip():
        return 1.0
    scan = _ink(crop)
    if scan.size <= 1:
        return 1.0
    rendered = _ink(render_text(text, scan.shape[0]))
    size = (scan.shape[1], scan.shape[0])
    rendered = cv2.resize(rendered.astype(np.uint8), size, interpolation=cv2.INTER_NEAREST) > 0
    # dilate so stroke-width differences between the type and the font do not dominate
    k = np.ones((max(3, scan.shape[0] // 25),) * 2, np.uint8)
    scan = cv2.dilate(scan.astype(np.uint8), k) > 0
    rendered = cv2.dilate(rendered.astype(np.uint8), k) > 0
    union = np.logical_or(scan, rendered).sum()
    return float(1 - np.logical_and(scan, rendered).sum() / union) if union else 1.0
