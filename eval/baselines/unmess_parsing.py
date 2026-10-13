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

    def configuration(self) -> dict[str, object]:
        return {
            "routing": (
                "PyMuPDF clean; Docling table/complex; VLM scan/low-density, uncovered ink, "
                "or escalation"
            ),
            "quality_review_threshold": self.settings.quality_review_threshold,
            "quality_visual_noise_threshold": self.settings.quality_visual_noise_threshold,
            "parser_text_density_threshold": self.settings.parser_text_density_threshold,
            "parser_image_coverage_threshold": self.settings.parser_image_coverage_threshold,
            "parser_scan_likelihood_threshold": self.settings.parser_scan_likelihood_threshold,
            "parser_table_likelihood_threshold": self.settings.parser_table_likelihood_threshold,
            "parser_complex_layout_threshold": self.settings.parser_complex_layout_threshold,
            "parser_uncovered_ink_threshold": self.settings.parser_uncovered_ink_threshold,
            "parser_max_skew_degrees": self.settings.parser_max_skew_degrees,
            "vision_model": self.settings.vision_model,
            "vision_raster_dpi": self.settings.vision_raster_dpi,
            "vision_timeout_s": self.settings.vision_timeout_s,
            "vision_retries_after_first_attempt": self.settings.vision_retries,
            "vision_failure_policy": (
                "return failed ParsedPage after all attempts; never drop page"
            ),
        }

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
