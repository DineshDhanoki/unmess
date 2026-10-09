"""Lazy, optional Docling page adapter with structured cells and spans."""

import importlib
import importlib.util
import os
from pathlib import Path
from time import perf_counter
from typing import Any

import pymupdf

from unmess.models import BBox, Block, Cell, Table
from unmess.parsing.base import ParsedPage, ParserUnavailable, normalized_bbox


class DoclingParser:
    name = "docling"

    def __init__(self) -> None:
        self._documents: dict[Path, Any] = {}

    @staticmethod
    def available() -> bool:
        return importlib.util.find_spec("docling") is not None

    def _document(self, pdf: Path) -> Any:
        if pdf not in self._documents:
            if not self.available():
                raise ParserUnavailable("Docling unavailable: install the [parsers] extra")
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            converter = importlib.import_module("docling.document_converter").DocumentConverter()
            self._documents[pdf] = converter.convert(str(pdf)).document
        return self._documents[pdf]

    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage:
        start = perf_counter()
        doc = self._document(pdf)
        with pymupdf.open(pdf) as source:
            page = source[page_number - 1]
            width, height = page.rect.width, page.rect.height
        blocks: list[Block] = []
        tables: list[Table] = []
        for index, (item, _level) in enumerate(doc.iterate_items()):
            provenance = [prov for prov in getattr(item, "prov", []) if prov.page_no == page_number]
            if not provenance:
                continue
            prov = provenance[0]
            raw_box = getattr(prov, "bbox", None)
            if raw_box is not None:
                # Docling's bbox origin may be bottom-left; normalize explicitly.
                left, right = float(raw_box.l), float(raw_box.r)
                origin = getattr(raw_box, "coord_origin", None)
                if getattr(origin, "value", origin) == "BOTTOMLEFT":
                    top, bottom = height - float(raw_box.t), height - float(raw_box.b)
                else:
                    top, bottom = float(raw_box.t), float(raw_box.b)
                try:
                    box = normalized_bbox(page_number, (left, top, right, bottom), width, height)
                except ValueError:
                    box = BBox(page=page_number, x0=0, y0=0, x1=1, y1=1)
            else:
                box = BBox(page=page_number, x0=0, y0=0, x1=1, y1=1)
            text = getattr(item, "text", "")
            if isinstance(text, str) and text.strip():
                blocks.append(
                    Block(
                        block_id=f"{page_number}:{index}",
                        kind="paragraph",
                        text=text.strip(),
                        bbox=box,
                    )
                )
            data = getattr(item, "data", None)
            if data is None or not hasattr(data, "table_cells"):
                continue
            cells = [
                Cell(
                    row=cell.start_row_offset_idx,
                    col=cell.start_col_offset_idx,
                    row_span=cell.row_span,
                    col_span=cell.col_span,
                    text=cell.text,
                    bbox=box,
                )
                for cell in data.table_cells
            ]
            if cells:
                blocks.append(
                    Block(
                        block_id=f"{page_number}:{index}:table",
                        kind="table",
                        text="\n".join(cell.text for cell in cells),
                        bbox=box,
                    )
                )
                tables.append(
                    Table(
                        table_id="line-items" if len(tables) == 0 else f"table-{index}",
                        page_numbers=[page_number],
                        cells=cells,
                        has_merged_cells=any(c.row_span > 1 or c.col_span > 1 for c in cells),
                    )
                )
        return ParsedPage(
            page_number=page_number,
            parser_name=self.name,
            text="\n".join(block.text for block in blocks),
            blocks=blocks,
            tables=tables,
            bboxes=[block.bbox for block in blocks],
            parse_time_s=perf_counter() - start,
        )
