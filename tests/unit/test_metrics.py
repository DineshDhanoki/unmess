"""Hand-built examples for each pure evaluation metric."""

import pytest

from eval.metrics.chunk_integrity import table_split_rate
from eval.metrics.citation_accuracy import citation_accuracy, is_relevant
from eval.metrics.latency import latency_per_page
from eval.metrics.ocr_cer import character_error_rate, word_error_rate
from eval.metrics.retrieval_recall import recall_at_k, reciprocal_rank
from eval.metrics.routing_efficiency import cheap_parser_share
from eval.metrics.table_f1 import table_cell_f1
from unmess.models import Answer, BBox, Cell, Chunk, Table


def box(page: int = 1, x0: float = 0.1, x1: float = 0.4) -> BBox:
    return BBox(page=page, x0=x0, y0=0.1, x1=x1, y1=0.4)


def chunk(text: str, bbox: BBox | None = None) -> Chunk:
    return Chunk(
        id=text,
        doc_id="d",
        text=text,
        page_numbers=[1],
        bboxes=[bbox or box()],
        parser_used="pymupdf",
        quality_score=1,
        content_hash=text,
    )


def test_table_cell_f1_handles_spans_and_missing_cells() -> None:
    expected = Table(
        table_id="t",
        page_numbers=[1],
        has_merged_cells=True,
        cells=[
            Cell(row=0, col=0, col_span=2, text="Header", bbox=box()),
            Cell(row=1, col=0, text="A", bbox=box()),
        ],
    )
    predicted = Table(
        table_id="t",
        page_numbers=[1],
        has_merged_cells=True,
        cells=[
            Cell(row=0, col=0, col_span=2, text="Header", bbox=box()),
            Cell(row=1, col=0, text="B", bbox=box()),
        ],
    )
    assert table_cell_f1([expected], [predicted]) == (0.5, 0.5, 0.5)


def test_table_f1_aligns_missing_merged_header_without_erasing_penalty() -> None:
    expected = Table(
        table_id="line-items",
        page_numbers=[1],
        has_merged_cells=True,
        cells=[
            Cell(row=0, col=0, col_span=3, text="Merged heading", bbox=box()),
            Cell(row=1, col=0, text="Item", bbox=box()),
            Cell(row=2, col=0, text="Fake item 1", bbox=box()),
        ],
    )
    parsed = Table(
        table_id="line-items",
        page_numbers=[1],
        cells=[
            Cell(row=0, col=0, text="Item", bbox=box()),
            Cell(row=1, col=0, text="Fake item 1", bbox=box()),
        ],
    )
    precision, recall, f1 = table_cell_f1([expected], [parsed])
    assert precision == 1.0
    assert recall == pytest.approx(2 / 3)
    assert f1 == pytest.approx(0.8)


def test_ocr_cer_and_retrieval() -> None:
    assert character_error_rate("kitten", "sitten") == pytest.approx(1 / 6)
    assert character_error_rate("", "") == 0
    assert word_error_rate("alpha beta gamma", "alpha theta gamma") == pytest.approx(1 / 3)
    assert word_error_rate("", "") == 0
    assert recall_at_k(["wrong", "right"], lambda item: item == "right", 1) == 0
    assert recall_at_k(["wrong", "right"], lambda item: item == "right", 2) == 1
    assert reciprocal_rank(["wrong", "right"], lambda item: item == "right") == 0.5


def test_chunk_integrity_citations_routing_and_latency() -> None:
    table = Table(
        table_id="t",
        page_numbers=[1],
        cells=[
            Cell(row=0, col=0, text="A", bbox=box()),
            Cell(row=1, col=0, text="B", bbox=box()),
        ],
    )
    assert table_split_rate([table], [chunk("A"), chunk("B")]) == 1
    assert table_split_rate([table], [chunk("A B")]) == 0
    answer = Answer(
        id="a",
        question="q",
        answer="x",
        answer_type="text",
        language="en",
        answering_pages=[1],
        answer_bboxes=[box()],
    )
    assert is_relevant(chunk("x"), answer)
    assert not is_relevant(chunk("x", box(x0=0.5, x1=0.8)), answer)
    assert citation_accuracy(answer, [1], [box()]) == 1
    assert citation_accuracy(answer, [2], [box(2)]) == 0
    assert cheap_parser_share(["pymupdf", "docling"]) == 0.5
    assert latency_per_page([0.1, 0.3]) == pytest.approx(0.2)
