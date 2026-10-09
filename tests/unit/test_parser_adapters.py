from pathlib import Path
from types import SimpleNamespace

import pytest

from unmess.parsing.base import ParserUnavailable
from unmess.parsing.docling_parser import DoclingParser
from unmess.parsing.pymupdf_parser import PyMuPDFParser

PDF = Path(__file__).resolve().parents[2] / "eval/datasets/pdf/synthetic-merged_table-00.pdf"


def test_pymupdf_blocks_have_normalized_source_boxes() -> None:
    page = PyMuPDFParser().parse_page(PDF, 1)
    assert page.success and page.text and page.blocks
    assert all(0 <= box.x0 < box.x1 <= 1 for box in page.bboxes)
    assert all(0 <= box.y0 < box.y1 <= 1 for box in page.bboxes)
    assert all(box.page == 1 for box in page.bboxes)


def test_docling_missing_extra_has_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = DoclingParser()
    monkeypatch.setattr(parser, "available", lambda: False)
    with pytest.raises(ParserUnavailable, match=r"\[parsers\]"):
        parser.parse_page(PDF, 1)


def test_docling_table_grid_and_span_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = DoclingParser()
    cell = SimpleNamespace(
        start_row_offset_idx=0,
        start_col_offset_idx=0,
        row_span=1,
        col_span=3,
        text="Merged heading",
    )
    item = SimpleNamespace(
        prov=[SimpleNamespace(page_no=1, bbox=None)],
        text="",
        data=SimpleNamespace(table_cells=[cell]),
    )
    document = SimpleNamespace(iterate_items=lambda: iter([(item, 0)]))
    monkeypatch.setattr(parser, "_document", lambda _pdf: document)
    result = parser.parse_page(PDF, 1)
    assert result.tables[0].cells[0].col_span == 3
    assert result.tables[0].has_merged_cells
