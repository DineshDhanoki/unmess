"""Phase 2 parsing adapter; retrieval is intentionally absent."""

from pathlib import Path

import pymupdf

from eval.baselines.base import ParsedDocument
from unmess.config import Settings
from unmess.parsing.router import PageRouter


class UnmessParsing:
    name = "unmess_parsing"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.router = PageRouter(settings)

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        with pymupdf.open(path) as document:
            page_count = len(document)
        result = ParsedDocument(page_texts=[], chunks=[])
        for page_number in range(1, page_count + 1):
            page = self.router.parse_page(path, page_number)
            result.page_results.append(page)
            result.page_texts.append(page.text)
            result.tables.extend(page.tables)
            result.page_durations_s.append(page.parse_time_s)
            result.parsers.append(page.parser_name)
        return result
