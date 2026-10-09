"""Fast digital-page extraction using PyMuPDF."""

from pathlib import Path
from time import perf_counter

import pymupdf

from unmess.models import Block
from unmess.parsing.base import ParsedPage, normalized_bbox


class PyMuPDFParser:
    name = "pymupdf"

    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage:
        start = perf_counter()
        with pymupdf.open(pdf) as document:
            page = document[page_number - 1]
            blocks: list[Block] = []
            for index, item in enumerate(page.get_text("blocks", sort=True)):
                if len(item) < 7 or item[6] != 0 or not str(item[4]).strip():
                    continue
                try:
                    box = normalized_bbox(
                        page_number,
                        (float(item[0]), float(item[1]), float(item[2]), float(item[3])),
                        page.rect.width,
                        page.rect.height,
                    )
                except ValueError:
                    continue
                blocks.append(
                    Block(
                        block_id=f"{page_number}:{index}",
                        kind="paragraph",
                        text=str(item[4]).strip(),
                        bbox=box,
                    )
                )
            return ParsedPage(
                page_number=page_number,
                parser_name=self.name,
                text="\n".join(block.text for block in blocks),
                blocks=blocks,
                bboxes=[block.bbox for block in blocks],
                parse_time_s=perf_counter() - start,
            )
