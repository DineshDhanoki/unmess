"""Plain PyMuPDF text extraction and fixed word windows."""

from pathlib import Path
from time import perf_counter

import pymupdf

from eval.baselines.base import ParsedDocument
from eval.baselines.naive_fixed_chunking import fixed_chunks


class PlainPyMuPDF:
    name = "pymupdf_fixed"

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        result = ParsedDocument(page_texts=[], chunks=[])
        with pymupdf.open(path) as document:
            for page in document:
                start = perf_counter()
                result.page_texts.append(page.get_text("text", sort=True).strip())
                result.chunks.extend(fixed_chunks(page, doc_id, "pymupdf"))
                result.page_durations_s.append(perf_counter() - start)
                result.parsers.append("pymupdf")
        return result
