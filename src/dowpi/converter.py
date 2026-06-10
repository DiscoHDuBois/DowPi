from pathlib import Path

import pymupdf
import pymupdf4llm

from dowpi.postprocess import clean


def convert_pdf(
    pdf_path: str | Path,
    *,
    pages: list[int] | None = None,
    write_images: bool = False,
    image_dir: str | Path | None = None,
    strip_repeated: bool = True,
) -> str:
    pdf_path = Path(pdf_path)
    with pymupdf.open(pdf_path) as doc:
        page_count = doc.page_count
    if pages:
        out_of_range = [p + 1 for p in pages if p < 0 or p >= page_count]
        if out_of_range:
            raise ValueError(
                f"pagine {out_of_range} fuori intervallo: il documento ne ha {page_count}"
            )

    kwargs: dict = {}
    if write_images:
        if image_dir is None:
            raise ValueError("write_images=True richiede image_dir")
        image_dir = Path(image_dir)
        image_dir.mkdir(parents=True, exist_ok=True)
        kwargs["write_images"] = True
        kwargs["image_path"] = str(image_dir)

    chunks = pymupdf4llm.to_markdown(
        str(pdf_path), pages=pages, page_chunks=True, show_progress=False, **kwargs
    )
    return clean([chunk["text"] for chunk in chunks], strip_repeated=strip_repeated)
