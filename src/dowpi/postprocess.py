import math
import re
from collections import Counter

_HEAD_LINES = 1
_FOOT_LINES = 1


def _normalize(line: str) -> str:
    text = re.sub(r"[*_`#>|\[\]()!]", "", line)
    text = re.sub(r"\d+", "#", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_page_rule(page: str) -> str:
    return re.sub(r"\n*-{3,}\s*$", "", page)


def remove_repeated_furniture(
    pages: list[str], *, min_pages: int = 3, threshold: float = 0.6
) -> list[str]:
    if len(pages) < min_pages:
        return list(pages)

    split = [page.splitlines() for page in pages]
    zones: list[tuple[list[int], list[int]]] = []
    head_counts: Counter[str] = Counter()
    foot_counts: Counter[str] = Counter()
    for lines in split:
        nonblank = [i for i, line in enumerate(lines) if line.strip()]
        head = nonblank[:_HEAD_LINES]
        foot = [i for i in nonblank[-_FOOT_LINES:] if i not in head]
        zones.append((head, foot))
        head_counts.update({_normalize(lines[i]) for i in head})
        foot_counts.update({_normalize(lines[i]) for i in foot})

    needed = max(min_pages, math.ceil(threshold * len(pages)))
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
    pages = [_strip_page_rule(page) for page in page_texts]
    if strip_repeated:
        pages = remove_repeated_furniture(pages)
    joined = "\n\n".join(page.strip("\n") for page in pages if page.strip())
    return tidy(joined)
