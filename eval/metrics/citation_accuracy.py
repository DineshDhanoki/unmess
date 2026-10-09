"""Citation geometry and retrieval relevance."""

from unmess.models import Answer, BBox, Chunk


def intersects(left: BBox, right: BBox) -> bool:
    return (
        left.page == right.page
        and left.x0 < right.x1
        and right.x0 < left.x1
        and left.y0 < right.y1
        and right.y0 < left.y1
    )


def is_relevant(chunk: Chunk, answer: Answer) -> bool:
    if not set(chunk.page_numbers).intersection(answer.answering_pages):
        return False
    return not answer.answer_bboxes or any(
        intersects(chunk_box, answer_box)
        for chunk_box in chunk.bboxes
        for answer_box in answer.answer_bboxes
    )


def citation_accuracy(answer: Answer, cited_pages: list[int], cited_bboxes: list[BBox]) -> float:
    if not set(cited_pages).intersection(answer.answering_pages):
        return 0.0
    if answer.answer_bboxes and not any(
        intersects(cited, expected) for cited in cited_bboxes for expected in answer.answer_bboxes
    ):
        return 0.0
    return 1.0
