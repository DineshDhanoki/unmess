"""Vision-model-only parsing baseline; page cache makes interrupted runs resumable."""

from pathlib import Path

import pymupdf

from eval.baselines.base import ParsedDocument
from unmess.config import Settings
from unmess.parsing.vlm_parser import VLMParser


class VLMEveryPage:
    name = "vlm_every_page"

    def __init__(self, settings: Settings) -> None:
        self.parser = VLMParser(settings)

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        del doc_id
        with pymupdf.open(path) as document:
            page_count = len(document)
        result = ParsedDocument(page_texts=[], chunks=[])
        for page_number in range(1, page_count + 1):
            page = self.parser.parse_page(path, page_number)
            result.page_results.append(page)
            result.page_texts.append(page.text)
            result.tables.extend(page.tables)
            result.page_durations_s.append(page.parse_time_s)
            result.parsers.append(page.parser_name)
        return result
