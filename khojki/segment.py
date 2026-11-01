"""Projection-profile line segmentation for printed and handwritten Khojki pages."""
from dataclasses import dataclass

import cv2
import numpy as np
from skimage.filters import threshold_sauvola

Box = tuple[int, int, int, int]


@dataclass
class Params:
    """Tunable thresholds, expressed relative to page size where possible."""
    sauvola_window: float = 0.02
    sauvola_k: float = 0.2
    min_speck: float = 0.006
    frame_col_fraction: float = 0.35
    frame_row_fraction: float = 0.5
    frame_search: float = 0.2
    max_skew: float = 3.0
    skew_step: float = 0.25
    smooth: float = 0.004
    valley: float = 0.08
    merge_ratio: float = 0.4
    pad: float = 0.2
    min_line_width: float = 0.1
    min_density: float = 0.01


def binarize(gray: np.ndarray, p: Params) -> np.ndarray:
    """Sauvola binarization with small specks removed; True = ink."""
    window = int(p.sauvola_window * max(gray.shape)) | 1
    ink = gray < threshold_sauvola(gray, window_size=window, k=p.sauvola_k)
    ink &= gray < 200
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    min_side = p.min_speck * max(gray.shape)
    keep = (stats[:, cv2.CC_STAT_WIDTH] >= min_side) | (stats[:, cv2.CC_STAT_HEIGHT] >= min_side)
    keep[0] = False
    return keep[labels]


def _inner_frame(profile: np.ndarray, length: int, fraction: float,
                 search: float) -> tuple[int, int] | None:
    """Find the innermost frame lines in a column or row profile."""
    hits = np.flatnonzero(profile > fraction * length)
    edge = int(search * len(profile))
    left = hits[hits < edge]
    right = hits[hits > len(profile) - edge]
    if len(left) == 0 or len(right) == 0:
        return None
    return int(left.max()), int(right.min())


def scan_bottom(gray: np.ndarray) -> int:
    """Last row of the scan; the PDF adds a pure-white caption strip below it."""
    white = (gray >= 252).mean(axis=1) > 0.5
    rows = np.flatnonzero(~white)
    return int(rows.max()) + 1 if len(rows) else gray.shape[0]


def find_text_block(ink: np.ndarray, p: Params, bottom: int | None = None) -> Box:
    """Return (x0, y0, x1, y1) inside the decorative frame, or a 10-90% width fallback."""
    h = bottom or ink.shape[0]
    ink = ink[:h]
    w = ink.shape[1]
    margin = int(0.01 * w)
    cols = _inner_frame(ink.sum(axis=0), h, p.frame_col_fraction, p.frame_search / 2)
    x0, x1 = (cols[0] + margin, cols[1] - margin) if cols else (int(0.1 * w), int(0.9 * w))
    rows = _inner_frame(ink[:, x0:x1].sum(axis=1), x1 - x0, p.frame_row_fraction, p.frame_search)
    y0, y1 = (rows[0] + margin, rows[1] - margin) if rows else (0, h)
    return x0, y0, x1, y1


def _rotate(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)


def estimate_skew(ink: np.ndarray, p: Params) -> float:
    """Angle in degrees that maximizes the variance of the row projection."""
    small = cv2.resize(ink.astype(np.uint8), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    angles = np.arange(-p.max_skew, p.max_skew + 1e-9, p.skew_step)
    scores = [_rotate(small, a).sum(axis=1).var() for a in angles]
    return float(angles[int(np.argmax(scores))])


def find_bands(ink: np.ndarray, p: Params) -> list[tuple[int, int]]:
    """Cut the row profile at valleys and return (top, bottom) bands."""
    profile = ink.sum(axis=1).astype(float)
    k = max(3, int(p.smooth * ink.shape[0]) | 1)
    profile = np.convolve(profile, np.ones(k) / k, mode="same")
    if profile.max() == 0:
        return []
    above = profile > p.valley * np.percentile(profile[profile > 0], 95)
    edges = np.flatnonzero(np.diff(np.r_[0, above.astype(int), 0]))
    bands = list(zip(edges[::2], edges[1::2]))
    return _merge_small(bands, p.merge_ratio)


def _merge_small(bands: list[tuple[int, int]], ratio: float) -> list[tuple[int, int]]:
    """Merge bands shorter than ratio x median height into their nearest neighbour."""
    bands = list(bands)
    while len(bands) > 1:
        heights = [b - a for a, b in bands]
        median = float(np.median(heights))
        small = [i for i, hgt in enumerate(heights) if hgt < ratio * median]
        if not small:
            break
        i = small[0]
        a, b = bands[i]
        gap_up = a - bands[i - 1][1] if i > 0 else np.inf
        gap_down = bands[i + 1][0] - b if i < len(bands) - 1 else np.inf
        j = i - 1 if gap_up <= gap_down else i + 1
        lo, hi = sorted((i, j))
        bands[lo:hi + 1] = [(bands[lo][0], bands[hi][1])]
    return bands


def segment(gray: np.ndarray, p: Params | None = None) -> list[Box]:
    """Return line boxes (x0, y0, x1, y1) in original page pixels, top to bottom."""
    lines, _ = segment_page(gray, p)
    return lines


def segment_page(gray: np.ndarray, p: Params | None = None) -> tuple[list[Box], dict]:
    """Segment a page and also return debug info (text block, skew angle)."""
    p = p or Params()
    ink = binarize(gray, p)
    bx0, by0, bx1, by1 = find_text_block(ink, p, scan_bottom(gray))
    block = ink[by0:by1, bx0:bx1]
    info = {"block": (bx0, by0, bx1, by1), "angle": 0.0}
    if block.sum() == 0:
        return [], info

    angle = estimate_skew(block, p)
    info["angle"] = angle
    straight = _rotate(block.astype(np.uint8), angle) > 0 if angle else block
    bands = find_bands(straight, p)
    if not bands:
        return [], info

    median_h = float(np.median([b - a for a, b in bands]))
    bh, bw = straight.shape
    inv = cv2.invertAffineTransform(cv2.getRotationMatrix2D((bw / 2, bh / 2), angle, 1.0))
    boxes: list[Box] = []
    for top, bottom in bands:
        if top <= 1 or bottom >= bh - 1:
            continue  # runs into the block edge: scanner shadow or border remnant
        rows = straight[top:bottom]
        cols = np.flatnonzero(rows.any(axis=0))
        if len(cols) < p.min_line_width * bw or rows.mean() < p.min_density:
            continue
        pad = int(p.pad * max(bottom - top, 0.5 * median_h))
        y0, y1 = max(0, top - pad), min(bh, bottom + pad)
        corners = np.array([[0, y0, 1], [bw, y0, 1], [0, y1, 1], [bw, y1, 1]], dtype=float)
        mapped = corners @ inv.T
        boxes.append((
            bx0 + max(0, int(mapped[:, 0].min())),
            by0 + max(0, int(mapped[:, 1].min())),
            bx0 + min(bw, int(mapped[:, 0].max())),
            by0 + min(bh, int(mapped[:, 1].max())),
        ))
    return boxes, info


def draw_overlay(gray: np.ndarray, boxes: list[Box]) -> np.ndarray:
    """Return a BGR copy of the page with numbered line boxes drawn."""
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    thick = max(2, gray.shape[1] // 600)
    for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), thick)
        cv2.putText(img, str(i), (max(0, x0 - 60 * thick // 2), y0 + 40), cv2.FONT_HERSHEY_SIMPLEX,
                    thick * 0.6, (0, 0, 255), thick)
    return img


def save_overlay(gray: np.ndarray, boxes: list[Box], path, scale: float = 0.25) -> None:
    """Write a downscaled overlay (small enough to commit, too small to reuse as a scan)."""
    img = draw_overlay(gray, boxes)
    cv2.imwrite(str(path), cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA))


def main() -> None:
    """Segment pages and write overlays plus line crops under results/."""
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    out = Path(a.out)
    (out / "overlays").mkdir(parents=True, exist_ok=True)
    (out / "lines").mkdir(parents=True, exist_ok=True)
    for path in a.pages:
        stem = Path(path).stem
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        boxes, info = segment_page(gray)
        save_overlay(gray, boxes, out / "overlays" / f"{stem}.png")
        for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
            cv2.imwrite(str(out / "lines" / f"{stem}_{i:02d}.png"), gray[y0:y1, x0:x1])
        print(f"{stem}: {len(boxes)} lines, skew {info['angle']:+.2f} deg, block {info['block']}")


if __name__ == "__main__":
    main()
