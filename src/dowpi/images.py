import hashlib
import itertools
import os
import re
import shutil
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pymupdf

from dowpi.postprocess import min_repeats

_IMAGE_LINK = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _local_image(link: str, image_dir: Path) -> Path | None:
    path = Path(link).resolve()
    return path if path.parent == image_dir and path.is_file() else None


def _rewrite(text: str, image_dir: Path, replace: Callable[[str, Path], str]) -> str:


    def sub(match: re.Match) -> str:
        alt, link = match.groups()
        path = _local_image(link, image_dir)
        return match.group(0) if path is None else replace(alt, path)

    return _IMAGE_LINK.sub(sub, text)


def image_stem(pdf_path: str | Path) -> str:
    return re.sub(r"[^\w.-]+", "_", Path(pdf_path).stem)


def drop_small_images(
    pages: list[str],
    image_dir: str | Path,
    page_rects: list[pymupdf.Rect],
    *,
    dpi: int,
    min_fraction: float = 0.05,
) -> list[str]:
    image_dir = Path(image_dir).resolve()
    scale = 72 / dpi

    def filter_page(page: str, rect: pymupdf.Rect) -> str:
        def replace(alt: str, path: Path) -> str:
            pix = pymupdf.Pixmap(str(path))
            if (
                pix.width * scale < min_fraction * rect.width
                or pix.height * scale < min_fraction * rect.height
            ):
                return ""
            return f"![{alt}]({path})"

        return _rewrite(page, image_dir, replace)

    return [filter_page(page, rect) for page, rect in zip(pages, page_rects)]


def dedupe_images(
    pages: list[str], image_dir: str | Path, *, drop_repeated: bool = True
) -> list[str]:
    #Unisce immagini identiche e rimuove quelle ripetute su quasi tutte le pagine.
    #Ogni contenuto distinto viene referenziato una sola volta.
    #drop_repeated per rumore (loghi, filigrane) vengono tolte del tutto.
    image_dir = Path(image_dir).resolve()
    canonical: dict[str, Path] = {}  
    keep_of: dict[Path, Path] = {} 
    pages_with: Counter[Path] = Counter()

    for page in pages:
        on_page = set()
        for _, link in _IMAGE_LINK.findall(page):
            path = _local_image(link, image_dir)
            if path is None:
                continue
            if path not in keep_of:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                keep_of[path] = canonical.setdefault(digest, path)
            on_page.add(keep_of[path])
        pages_with.update(on_page)

    dropped: set[Path] = set()
    if drop_repeated:
        needed = min_repeats(len(pages))
        if needed is not None:
            dropped = {path for path, count in pages_with.items() if count >= needed}

    emitted: set[Path] = set()

    def replace(alt: str, path: Path) -> str:
        keep = keep_of[path]
        if keep in dropped or keep in emitted:
            return ""
        emitted.add(keep)
        return f"![{alt}]({keep})"

    return [_rewrite(page, image_dir, replace) for page in pages]


def publish_images(
    pages: list[str],
    staging_dir: str | Path,
    image_dir: str | Path,
    *,
    stem: str,
    page_numbers: list[int],
) -> list[str]:
    staging_dir = Path(staging_dir).resolve()
    image_dir = Path(image_dir)
    previous = re.compile(rf"{re.escape(stem)}-p\d+-\d+\.\w+")
    if image_dir.is_dir():
        for old in image_dir.iterdir():
            if old.is_file() and previous.fullmatch(old.name):
                old.unlink()

    def publish_page(page: str, number: int) -> str:
        counter = itertools.count(1)

        def replace(alt: str, path: Path) -> str:
            target = image_dir / f"{stem}-p{number}-{next(counter)}{path.suffix}"
            image_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(path, target)
            return f"![{alt}]({target})"

        return _rewrite(page, staging_dir, replace)

    return [publish_page(page, number) for page, number in zip(pages, page_numbers)]


def relink_images(markdown: str, image_dir: str | Path, base_dir: str | Path) -> str:
    
    image_dir = Path(image_dir).resolve()
    rel = Path(os.path.relpath(image_dir, Path(base_dir).resolve())).as_posix()
    return _rewrite(markdown, image_dir, lambda alt, path: f"![{alt}]({rel}/{path.name})")
