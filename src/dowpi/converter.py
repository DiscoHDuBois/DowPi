import tempfile
from pathlib import Path

import pymupdf
import pymupdf4llm

from dowpi.images import dedupe_images, drop_small_images, image_stem, publish_images
from dowpi.postprocess import clean

_IMAGE_DPI = 150


def convert_pdf(
    pdf_path: str | Path,
    *,
    pages: list[int] | None = None,
    write_images: bool = False,
    image_dir: str | Path | None = None,
    strip_repeated: bool = True,
    min_image_size: float = 0.05,
) -> str:
    pdf_path = Path(pdf_path)
    if write_images and image_dir is None:
        raise ValueError("write_images=True richiede image_dir")

    with pymupdf.open(pdf_path) as doc:
        page_count = doc.page_count
        if pages:
            out_of_range = [p + 1 for p in pages if p < 0 or p >= page_count]
            if out_of_range:
                raise ValueError(
                    f"pagine {out_of_range} fuori intervallo: il documento ne ha {page_count}"
                )
        page_rects = [page.rect for page in doc]

    options = {"pages": pages, "page_chunks": True, "show_progress": False}
    if not write_images:
        chunks = pymupdf4llm.to_markdown(str(pdf_path), **options)
        return clean([chunk["text"] for chunk in chunks], strip_repeated=strip_repeated)

    # le immagini passano da una cartella temporanea: in image_dir finiscono solo quelle tenute
    with tempfile.TemporaryDirectory(prefix="dowpi-") as staging:
        chunks = pymupdf4llm.to_markdown(
            str(pdf_path), write_images=True, image_path=staging, dpi=_IMAGE_DPI, **options
        )
        page_numbers = [chunk["metadata"]["page_number"] for chunk in chunks]
        page_texts = [chunk["text"] for chunk in chunks]
        page_texts = drop_small_images(
            page_texts,
            staging,
            [page_rects[n - 1] for n in page_numbers],
            dpi=_IMAGE_DPI,
            min_fraction=min_image_size,
        )
        page_texts = dedupe_images(page_texts, staging, drop_repeated=strip_repeated)
        page_texts = publish_images(
            page_texts, staging, image_dir, stem=image_stem(pdf_path), page_numbers=page_numbers
        )
    return clean(page_texts, strip_repeated=strip_repeated)
