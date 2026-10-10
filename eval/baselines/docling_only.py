"""Optional Docling-only parser baseline."""

import hashlib
import importlib.util
from pathlib import Path
from time import perf_counter

import pymupdf

from eval.baselines.base import ParsedDocument
from unmess.config import Settings
from unmess.models import BBox, Cell, Chunk, Table
from unmess.parsing.base import ParsedPage
from unmess.parsing.docling_parser import make_docling_converter


class DoclingOnly:
    name = "docling_only"

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("docling") is not None

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        if not self.available():
            raise RuntimeError("skipped: optional dependency not installed")
        start = perf_counter()
        document = (
            make_docling_converter(Settings().docling_artifacts_path).convert(str(path)).document
        )
        page_count = len(pymupdf.open(path))
        page_texts = ["" for _ in range(page_count)]
        for item, _level in document.iterate_items():
            text = getattr(item, "text", "")
            for prov in getattr(item, "prov", []):
                page_no = getattr(prov, "page_no", 0)
                if isinstance(text, str) and text and 1 <= page_no <= page_count:
                    page_texts[page_no - 1] += text + "\n"
        chunks: list[Chunk] = []
        tables: list[Table] = []
        for table_index, item in enumerate(document.tables):
            provenance = getattr(item, "prov", [])
            page_no = getattr(provenance[0], "page_no", 1) if provenance else 1
            cells = [
                Cell(
                    row=cell.start_row_offset_idx,
                    col=cell.start_col_offset_idx,
                    row_span=cell.row_span,
                    col_span=cell.col_span,
                    text=cell.text,
                    bbox=BBox(page=page_no, x0=0, y0=0, x1=1, y1=1),
                )
                for cell in item.data.table_cells
            ]
            if cells:
                tables.append(
                    Table(
                        table_id="line-items" if table_index == 0 else f"table-{table_index}",
                        page_numbers=[page_no],
                        cells=cells,
                        has_merged_cells=any(
                            cell.row_span > 1 or cell.col_span > 1 for cell in cells
                        ),
                    )
                )
        for page_no, text in enumerate(page_texts, 1):
            if not text.strip():
                continue
            chunks.append(
                Chunk(
                    id=f"{doc_id}:{page_no}:docling",
                    doc_id=doc_id,
                    text=text.strip(),
                    page_numbers=[page_no],
                    bboxes=[BBox(page=page_no, x0=0, y0=0, x1=1, y1=1)],
                    parser_used="docling",
                    quality_score=1,
                    content_hash=hashlib.sha256(text.encode()).hexdigest(),
                )
            )
        elapsed = perf_counter() - start
        return ParsedDocument(
            page_texts=page_texts,
            chunks=chunks,
            tables=tables,
            page_durations_s=[elapsed / page_count] * page_count,
            parsers=["docling"] * page_count,
            page_results=[
                ParsedPage(
                    page_number=index,
                    parser_name="docling",
                    text=text,
                    success=bool(text.strip()),
                    error=None if text.strip() else "no extracted text",
                )
                for index, text in enumerate(page_texts, 1)
            ],
        )
