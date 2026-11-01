from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from khojki.segment import segment

PAGES = Path(__file__).resolve().parents[1] / "data" / "pages"


def test_blank_page_has_no_lines():
    page = np.full((3300, 2500), 235, dtype=np.uint8)
    rng = np.random.default_rng(0)
    page = np.clip(page + rng.normal(0, 6, page.shape), 0, 255).astype(np.uint8)
    assert segment(page) == []


def _page(n: int) -> np.ndarray:
    path = PAGES / f"page_{n:02d}.png"
    if not path.exists():
        pytest.skip("run `make pages` first")
    return np.asarray(Image.open(path).convert("L"))


def test_blank_cover_has_no_lines():
    assert segment(_page(8)) == []


def test_printed_cover_does_not_crash():
    assert isinstance(segment(_page(7)), list)


def test_page_18_line_count():
    # 16 text lines inside the frame; the "(2)" page header sits above the frame
    assert 16 <= len(segment(_page(18))) <= 22
