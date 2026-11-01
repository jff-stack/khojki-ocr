"""Render the sample PDF to page PNGs (300 DPI) plus page 18 at 400 DPI."""
import argparse
from pathlib import Path

import pypdfium2 as pdfium

DEFAULT_PDF = "inputs/sample_khojki_script_vatiations.pdf"


def render_page(pdf: pdfium.PdfDocument, index: int, dpi: int, out: Path) -> None:
    """Render one 0-based page to an 8-bit grayscale PNG."""
    image = pdf[index].render(scale=dpi / 72, grayscale=True).to_pil()
    image.save(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", default=DEFAULT_PDF)
    ap.add_argument("--out", default="data/pages")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--pages", help="comma-separated 1-based pages (default: all)")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(a.pdf)
    pages = [int(p) for p in a.pages.split(",")] if a.pages else range(1, len(pdf) + 1)
    for n in pages:
        target = out / f"page_{n:02d}.png"
        if not target.exists():
            render_page(pdf, n - 1, a.dpi, target)
    oracle = out / "page_18_400dpi.png"
    if not oracle.exists() and len(pdf) >= 18:
        render_page(pdf, 17, 400, oracle)
    print(f"{len(pdf)} pages in {a.pdf} -> {out}/")


if __name__ == "__main__":
    main()
