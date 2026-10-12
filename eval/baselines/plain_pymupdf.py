"""Plain PyMuPDF text extraction and fixed word windows."""

from pathlib import Path
from time import perf_counter

import pymupdf

from eval.baselines.base import ParsedDocument
from eval.baselines.naive_fixed_chunking import fixed_chunks
from unmess.models import BBox, Cell, Table
from unmess.parsing.base import ParsedPage


class PlainPyMuPDF:
    name = "pymupdf_fixed"

    @staticmethod
    def configuration() -> dict[str, object]:
        return {
            "text": "page.get_text('text', sort=True)",
            "tables": "page.find_tables()",
            "table_strategy": "PyMuPDF defaults (vertical=lines, horizontal=lines)",
            "chunking": "16 words, 3-word overlap",
            "ocr": False,
        }

    @staticmethod
    def _tables(page: pymupdf.Page) -> list[Table]:
        found = page.find_tables()
        tables: list[Table] = []
        for table_index, candidate in enumerate(found.tables):
            values = candidate.extract()
            cells: list[Cell] = []
            for row_index, row in enumerate(values):
                for col_index, value in enumerate(row):
                    rectangle = candidate.rows[row_index].cells[col_index]
                    text = (value or "").strip()
                    if rectangle is None or not text:
                        continue
                    x0, y0, x1, y1 = rectangle
                    cells.append(
                        Cell(
                            row=row_index,
                            col=col_index,
                            text=text,
                            bbox=BBox(
                                page=page.number + 1,
                                x0=max(0.0, x0 / page.rect.width),
                                y0=max(0.0, y0 / page.rect.height),
                                x1=min(1.0, x1 / page.rect.width),
                                y1=min(1.0, y1 / page.rect.height),
                            ),
                        )
                    )
            if cells:
                tables.append(
                    Table(
                        table_id=("line-items" if table_index == 0 else f"table-{table_index}"),
                        page_numbers=[page.number + 1],
                        cells=cells,
                    )
                )
        return tables

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        result = ParsedDocument(page_texts=[], chunks=[])
        with pymupdf.open(path) as document:
            for page in document:
                start = perf_counter()
                text = page.get_text("text", sort=True).strip()
                tables = self._tables(page)
                result.page_texts.append(text)
                result.tables.extend(tables)
                result.chunks.extend(fixed_chunks(page, doc_id, "pymupdf"))
                result.page_durations_s.append(perf_counter() - start)
                result.parsers.append("pymupdf")
                result.page_results.append(
                    ParsedPage(
                        page_number=page.number + 1,
                        parser_name="pymupdf",
                        text=text,
                        tables=tables,
                        success=bool(text),
                        error=None if text else "no embedded text",
                    )
                )
        return result
