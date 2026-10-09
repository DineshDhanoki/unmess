"""Fixed word windows with geometry retained solely for evaluation."""

import hashlib

import pymupdf

from unmess.models import BBox, Chunk


def fixed_chunks(
    page: pymupdf.Page, doc_id: str, parser: str, size: int = 16, overlap: int = 3
) -> list[Chunk]:
    if size <= overlap or overlap < 0:
        raise ValueError("size must exceed nonnegative overlap")
    words = page.get_text("words", sort=True)
    result: list[Chunk] = []
    for start in range(0, len(words), size - overlap):
        window = words[start : start + size]
        if not window:
            break
        text = " ".join(str(word[4]) for word in window)
        box = BBox(
            page=page.number + 1,
            x0=max(0.0, min(float(word[0]) for word in window) / page.rect.width),
            y0=max(0.0, min(float(word[1]) for word in window) / page.rect.height),
            x1=min(1.0, max(float(word[2]) for word in window) / page.rect.width),
            y1=min(1.0, max(float(word[3]) for word in window) / page.rect.height),
        )
        result.append(
            Chunk(
                id=f"{doc_id}:{page.number + 1}:{start}",
                doc_id=doc_id,
                text=text,
                page_numbers=[page.number + 1],
                bboxes=[box],
                parser_used=parser,
                quality_score=1.0,
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
            )
        )
        if start + size >= len(words):
            break
    return result
