"""Vision-model-only parsing baseline; page cache makes interrupted runs resumable."""

from pathlib import Path

import pymupdf

from eval.baselines.base import ParsedDocument
from unmess.config import Settings
from unmess.parsing.vlm_parser import PROMPT_VERSION, VLMParser


class VLMEveryPage:
    name = "vlm_every_page"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.parser = VLMParser(settings, allow_model_calls=False)

    def configuration(self) -> dict[str, object]:
        return {
            "model": self.settings.vision_model,
            "raster_dpi": self.settings.vision_raster_dpi,
            "prompt_version": PROMPT_VERSION,
            "response_contract": "strict JSON object with Markdown transcription",
            "table_contract": "pipe-table Markdown parsed into Table cells; spans unavailable",
            "cache": "read-only; cache misses are failures; no model rerun",
        }

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
