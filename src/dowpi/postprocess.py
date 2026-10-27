import math
import re
from collections import Counter

_HEAD_LINES = 1
_FOOT_LINES = 1
_MIN_PAGES = 3
_THRESHOLD = 0.6
_IMAGE_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$")
# segnaposto di pymupdf4llm per immagini non estratte
_OMITTED_PICTURE = re.compile(
    r"^[ \t]*\*\*==> picture \[[^\]]*\] intentionally omitted <==\*\*[ \t]*\n?", re.MULTILINE
)
# testo trovato dentro un'immagine
_PICTURE_TEXT = re.compile(
    r"\*\*----- Start of picture text -----\*\*<br>\n(.*?)"
    r"\*\*----- End of picture text -----\*\*<br>\n?",
    re.DOTALL,
)
_PICTURE_TEXT_LABEL = "> [image text]"


def min_repeats(
    page_count: int, *, min_pages: int = _MIN_PAGES, threshold: float = _THRESHOLD
) -> int | None:
    if page_count < min_pages:
        return None
    return max(min_pages, math.ceil(threshold * page_count))


def _normalize(line: str) -> str:
    text = re.sub(r"[*_`#>|\[\]()!]", "", line)
    text = re.sub(r"\d+", "#", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_page_rule(page: str) -> str:
    return re.sub(r"\n*-{3,}\s*$", "", page)


def compact_picture_text(page: str) -> str:
    def replace(match: re.Match) -> str:
        lines = [line.strip() for line in re.split(r"<br>|\n", match.group(1))]
        quoted = [f"> {line}" for line in lines if line]
        return "\n".join([_PICTURE_TEXT_LABEL, *quoted]) + "\n" if quoted else ""

    return _PICTURE_TEXT.sub(replace, page)


def _protected_lines(lines: list[str]) -> set[int]:
    protected = set()
    in_picture_text = False
    for i, line in enumerate(lines):
        if line == _PICTURE_TEXT_LABEL:
            in_picture_text = True
        elif not line.startswith(">"):
            in_picture_text = False
        if in_picture_text or _IMAGE_LINE.match(line):
            protected.add(i)
    return protected


def remove_repeated_furniture(
    pages: list[str], *, min_pages: int = _MIN_PAGES, threshold: float = _THRESHOLD
) -> list[str]:
    needed = min_repeats(len(pages), min_pages=min_pages, threshold=threshold)
    if needed is None:
        return list(pages)

    split = [page.splitlines() for page in pages]
    zones: list[tuple[list[int], list[int]]] = []
    head_counts: Counter[str] = Counter()
    foot_counts: Counter[str] = Counter()
    for lines in split:
        protected = _protected_lines(lines)
        nonblank = [i for i, line in enumerate(lines) if line.strip()]
        head = [i for i in nonblank[:_HEAD_LINES] if i not in protected]
        foot = [i for i in nonblank[-_FOOT_LINES:] if i not in head and i not in protected]
        zones.append((head, foot))
        head_counts.update({_normalize(lines[i]) for i in head})
        foot_counts.update({_normalize(lines[i]) for i in foot})

    drop_head = {key for key, count in head_counts.items() if count >= needed and key}
    drop_foot = {key for key, count in foot_counts.items() if count >= needed and key}

    cleaned = []
    for lines, (head, foot) in zip(split, zones):
        drop = {i for i in head if _normalize(lines[i]) in drop_head}
        drop |= {i for i in foot if _normalize(lines[i]) in drop_foot}
        cleaned.append("\n".join(line for i, line in enumerate(lines) if i not in drop))
    return cleaned


def tidy(text: str) -> str:
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip("\n")
    return text + "\n" if text else ""


def clean(page_texts: list[str], *, strip_repeated: bool = True) -> str:
    pages = [
        compact_picture_text(_OMITTED_PICTURE.sub("", _strip_page_rule(page)))
        for page in page_texts
    ]
    if strip_repeated:
        pages = remove_repeated_furniture(pages)
    joined = "\n\n".join(page.strip("\n") for page in pages if page.strip())
    return tidy(joined)
