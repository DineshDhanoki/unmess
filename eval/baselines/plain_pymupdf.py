"""Plain PyMuPDF text extraction and fixed word windows."""

from pathlib import Path
from time import perf_counter

import pymupdf

from eval.baselines.base import ParsedDocument
from eval.baselines.naive_fixed_chunking import fixed_chunks
from unmess.parsing.base import ParsedPage


class PlainPyMuPDF:
    name = "pymupdf_fixed"

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        result = ParsedDocument(page_texts=[], chunks=[])
        with pymupdf.open(path) as document:
            for page in document:
                start = perf_counter()
                text = page.get_text("text", sort=True).strip()
                result.page_texts.append(text)
                result.chunks.extend(fixed_chunks(page, doc_id, "pymupdf"))
                result.page_durations_s.append(perf_counter() - start)
                result.parsers.append("pymupdf")
                result.page_results.append(
                    ParsedPage(
                        page_number=page.number + 1,
                        parser_name="pymupdf",
                        text=text,
                        success=bool(text),
                        error=None if text else "no embedded text",
                    )
                )
        return result
