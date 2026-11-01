"""Render corpus lines with Noto Sans Khojki and apply scan-like damage."""
import argparse
import io
import random
import time
from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

from khojki import log_experiment
from khojki.charset import MARKS, NOT_IN_FONT, NUKTA, SHADDA, VIRAMA

FONT = "tools/NotoSansKhojki-Regular.ttf"
CORPUS = Path("data/corpus/corpus.txt")
TEXTURE_PAGES = ["data/pages/page_16.png", "data/pages/page_08.png"]
LINE_HEIGHT = 120

_textures: list[np.ndarray] = []


def has_dotted_circle(text: str) -> bool:
    """True if HarfBuzz would draw a dotted circle: virama or shadda after another mark."""
    for prev, cur in zip(text, text[1:]):
        if ord(cur) in (VIRAMA, SHADDA) and ord(prev) in MARKS - {NUKTA}:
            return True
    return False


def render_clean(text: str, size: int, rng: random.Random) -> np.ndarray:
    """Draw one line black on white with random padding; returns uint8 grayscale."""
    font = ImageFont.truetype(FONT, size, layout_engine=ImageFont.Layout.RAQM)
    x0, y0, x1, y1 = font.getbbox(text)
    pad_x = rng.randint(size // 4, size)
    pad_top = rng.randint(size // 6, size // 2)
    pad_bottom = rng.randint(size // 6, size // 2)
    w, h = x1 - x0 + 2 * pad_x, y1 - y0 + pad_top + pad_bottom
    img = Image.new("L", (w, h), 255)
    ImageDraw.Draw(img).text((pad_x - x0, pad_top - y0), text, font=font, fill=0)
    return np.asarray(img)


def load_textures(paths: list[str], n: int = 60, seed: int = 0) -> list[np.ndarray]:
    """Cut ink-free paper patches from real page scans."""
    rng = np.random.default_rng(seed)
    patches = []
    for p in paths:
        if not Path(p).exists():
            continue
        page = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        h, w = page.shape
        for _ in range(4000):
            ph, pw = 160, 900
            y, x = rng.integers(0, h - ph), rng.integers(0, w - pw)
            patch = page[y:y + ph, x:x + pw]
            if patch.mean() > 120 and patch.min() > patch.mean() - 60 and patch.std() < 14:
                patches.append(patch)
            if len(patches) >= n * (paths.index(p) + 1):
                break
    return patches


def damage(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Apply rotation, ink spread, blur, paper texture, noise, contrast and JPEG artifacts."""
    h, w = img.shape
    angle = rng.uniform(-1.5, 1.5)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    img = cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)

    op = rng.random()
    kernel = np.ones((2, 2), np.uint8)
    if op < 0.3:
        img = cv2.erode(img, kernel)
    elif op < 0.6:
        img = cv2.dilate(img, kernel)

    sigma = rng.uniform(0, 1.2)
    if sigma > 0.1:
        img = cv2.GaussianBlur(img, (0, 0), sigma)

    out = img.astype(np.float32) / 255
    if _textures and rng.random() < 0.85:
        tex = _textures[rng.randrange(len(_textures))]
        tex = cv2.resize(tex, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        out = out * (tex / 255)
    else:
        out = out * rng.uniform(0.75, 1.0)

    lo, hi = rng.uniform(0.0, 0.25), rng.uniform(0.8, 1.0)
    out = lo + out * (hi - lo)

    amount = rng.uniform(0, 0.01)
    noise = np.random.default_rng(rng.randrange(2**32)).random(out.shape)
    out[noise < amount / 2] = rng.uniform(0, 0.3)
    out[noise > 1 - amount / 2] = 1.0

    img = np.clip(out * 255, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, format="JPEG", quality=rng.randint(30, 80))
    return np.asarray(Image.open(buf).convert("L"))


def normalize_height(img: np.ndarray, height: int = LINE_HEIGHT) -> np.ndarray:
    """Scale a line image to a fixed height, keeping the aspect ratio."""
    h, w = img.shape
    return cv2.resize(img, (max(1, round(w * height / h)), height), interpolation=cv2.INTER_AREA)


def _job(args: tuple[int, str, int, bool, str]) -> None:
    i, text, seed, clean, out = args
    rng = random.Random(seed)
    img = render_clean(text, rng.randint(28, 48), rng)
    if not clean:
        img = damage(img, rng)
    img = normalize_height(img)
    stem = Path(out) / f"{i:05d}"
    cv2.imwrite(f"{stem}.png", img)
    Path(f"{stem}.gt.txt").write_text(text + "\n", encoding="utf-8")


def _init(texture_paths: list[str]) -> None:
    global _textures
    _textures = load_textures(texture_paths)


def contact_sheet(paths: list[Path], out: str, cols: int = 2, width: int = 1100) -> None:
    """Stack sample images into a grid for a quick visual check."""
    tiles = []
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        img = img[:, :width] if img.shape[1] >= width else np.pad(
            img, ((0, 0), (0, width - img.shape[1])), constant_values=255)
        tiles.append(np.pad(img, 6, constant_values=180))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out, np.vstack(rows))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--out", default="data/synth/damaged")
    ap.add_argument("--clean", action="store_true", help="no damage")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--sheet", default="results/synth_samples.png")
    a = ap.parse_args()

    if not features.check_feature("raqm"):
        raise SystemExit("Pillow was built without raqm; Khojki would render incorrectly")
    start = time.time()
    lines = [ln.split("\t", 1)[1] for ln in CORPUS.read_text(encoding="utf-8").splitlines()]
    assert not any(ord(c) in NOT_IN_FONT for ln in lines for c in ln), "U+11241 is not in the font"
    rng = random.Random(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(i, rng.choice(lines), rng.randrange(2**31), a.clean, str(out)) for i in range(a.n)]
    with Pool(a.workers, initializer=_init, initargs=(TEXTURE_PAGES,)) as pool:
        pool.map(_job, jobs, chunksize=64)
    minutes = (time.time() - start) / 60
    kind = "clean" if a.clean else "damaged"
    log_experiment(f"render_{kind}", f"n={a.n} font=28-48px height={LINE_HEIGHT} seed={a.seed}",
                   "images", a.n, minutes)
    if not a.clean:
        contact_sheet(sorted(out.glob("*.png"))[:12], a.sheet)
        print(f"contact sheet: {a.sheet}")
    print(f"{a.n} {kind} lines -> {out} in {minutes:.1f} min")


if __name__ == "__main__":
    main()
