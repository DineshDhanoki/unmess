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
        self.parser = VLMParser(settings)

    def configuration(self) -> dict[str, object]:
        return {
            "model": self.settings.vision_model,
            "raster_dpi": self.settings.vision_raster_dpi,
            "temperature": self.settings.vision_temperature,
            "repeat_penalty": self.settings.vision_repeat_penalty,
            "repeat_last_n": self.settings.vision_repeat_last_n,
            "num_predict": self.settings.vision_num_predict,
            "prompt_version": PROMPT_VERSION,
            "timeout_s": self.settings.vision_timeout_s,
            "retries_after_first_attempt": self.settings.vision_retries,
            "failure_policy": "return failed ParsedPage after all attempts; never drop page",
            "response_contract": "strict JSON object with Markdown transcription",
            "table_contract": "pipe-table Markdown parsed into Table cells; spans unavailable",
            "cache": "read/write; key includes page image, model tag, and prompt version",
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
