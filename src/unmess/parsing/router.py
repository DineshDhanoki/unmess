"""Per-page parser selection and single-step quality escalation."""

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import structlog

from unmess.config import Settings
from unmess.parsing.base import ParsedPage, Parser, ParserAttempt
from unmess.parsing.docling_parser import DoclingParser
from unmess.parsing.page_features import PageFeatures, inspect_page
from unmess.parsing.pymupdf_parser import PyMuPDFParser
from unmess.parsing.vlm_parser import VLMParser
from unmess.quality.gates import review_gate
from unmess.quality.scorer import combine_signals, score_page

logger = structlog.get_logger(__name__)


class PageRouter:
    def __init__(
        self,
        settings: Settings,
        pymupdf_parser: Parser | None = None,
        docling_parser: Parser | None = None,
        vlm_parser: Parser | None = None,
        feature_provider: Callable[[Path, int], PageFeatures] = inspect_page,
    ) -> None:
        self.settings = settings
        self.parsers: dict[str, Parser] = {
            "pymupdf": pymupdf_parser or PyMuPDFParser(),
            "docling": docling_parser or DoclingParser(settings.docling_artifacts_path),
            "vlm": vlm_parser or VLMParser(settings),
        }
        self.feature_provider = feature_provider

    def _first_route(self, features: PageFeatures) -> tuple[str, str]:
        settings = self.settings
        if (
            features.scan_likelihood >= settings.parser_scan_likelihood_threshold
            or features.image_coverage >= settings.parser_image_coverage_threshold
            or features.embedded_text_density < settings.parser_text_density_threshold
        ):
            return "vlm", "scan_or_low_text_density"
        if features.table_likelihood >= settings.parser_table_likelihood_threshold:
            return "docling", "complex_layout_or_table"
        if features.uncovered_ink_ratio >= settings.parser_uncovered_ink_threshold:
            return "vlm", "rendered_ink_not_covered_by_text_layer"
        if (
            features.layout_complexity >= settings.parser_complex_layout_threshold
            or abs(features.skew_degrees) > settings.parser_max_skew_degrees
        ):
            return "docling", "complex_layout_or_table"
        return "pymupdf", "clean_digital_text"

    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage:
        started = perf_counter()
        try:
            features = self.feature_provider(pdf, page_number)
        except Exception as exc:
            result = ParsedPage.failed(page_number, "feature_extraction", str(exc))
            result.parse_time_s = perf_counter() - started
            result.review_reasons = ["feature_extraction_failed", "parser_failed"]
            return result
        parser_name, reason = self._first_route(features)
        attempts: list[ParserAttempt] = []
        previous_attempt: ParsedPage | None = None
        for step in range(2):
            try:
                parsed = self.parsers[parser_name].parse_page(pdf, page_number)
            except Exception as exc:
                parsed = ParsedPage.failed(page_number, parser_name, f"{type(exc).__name__}: {exc}")
            score = score_page(parsed, features, self.settings)
            parsed.quality_score = score.score
            parsed.quality_signals = score.signals
            parsed.source_features = {
                name: value for name, value in asdict(features).items() if name != "embedded_text"
            }
            attempts.append(
                ParserAttempt(
                    parser=parser_name,
                    reason=reason,
                    succeeded=parsed.success,
                    quality_score=score.score,
                    error=parsed.error,
                    duration_s=parsed.parse_time_s,
                    cache_hit=parsed.cache_hit,
                )
            )
            escalation_signals = {
                name: value
                for name, value in score.signals.items()
                if name != "cross_page_table_continuity"
            }
            escalation_score = combine_signals(escalation_signals)
            if (
                step == 0
                and parser_name != "vlm"
                and (
                    not parsed.success or escalation_score < self.settings.quality_review_threshold
                )
            ):
                previous_attempt = parsed
                parser_name, reason = (
                    "vlm",
                    f"escalated_after_{attempts[-1].parser}_failure_or_low_score",
                )
                continue
            parsed.attempts = attempts
            parsed.previous_attempt = previous_attempt
            parsed.route_reason = reason
            parsed.parse_time_s = perf_counter() - started
            report = review_gate(pdf.stem, parsed, features, self.settings)
            parsed.review_reasons = report.reasons
            logger.info(
                "page_routed",
                document=pdf.name,
                page=page_number,
                parser=parsed.parser_name,
                reason=reason,
                score=parsed.quality_score,
                attempts=[attempt.parser for attempt in attempts],
            )
            return parsed
        raise AssertionError("unreachable routing state")
