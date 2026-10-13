"""Transparent page confidence with missing-signal weight renormalization."""

import re
from dataclasses import dataclass

from unmess.config import Settings
from unmess.parsing.base import ParsedPage
from unmess.parsing.page_features import (
    PageFeatures,
    character_plausibility,
    garbled_ratio,
    script_plausibility,
)

WEIGHTS = {
    "text_coverage": 0.25,
    "character_integrity": 0.10,
    "character_plausibility": 0.20,
    "script_plausibility": 0.05,
    "text_ink_alignment": 0.15,
    "table_consistency": 0.15,
    "parser_confidence": 0.05,
    "parser_agreement": 0.05,
    "visual_clarity": 0.30,
    "cross_page_table_continuity": 0.40,
}


@dataclass(frozen=True)
class ScoreResult:
    score: float
    signals: dict[str, float]


def combine_signals(signals: dict[str, float]) -> float:
    """Combine available signals while renormalizing missing-signal weights."""
    known = {name: value for name, value in signals.items() if name in WEIGHTS}
    weight = sum(WEIGHTS[name] for name in known)
    if not weight:
        return 0.0
    return sum(value * WEIGHTS[name] for name, value in known.items()) / weight


def _words(value: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", value.casefold()))


def _table_consistency(page: ParsedPage) -> float:
    if not page.tables:
        return 0.0
    values = []
    for table in page.tables:
        occupied: set[tuple[int, int]] = set()
        valid = 0
        for cell in table.cells:
            positions = {
                (row, col)
                for row in range(cell.row, cell.row + cell.row_span)
                for col in range(cell.col, cell.col + cell.col_span)
            }
            if not positions.intersection(occupied) and cell.text.strip():
                valid += 1
            occupied.update(positions)
        values.append(valid / len(table.cells))
    return sum(values) / len(values)


def score_page(page: ParsedPage, features: PageFeatures, settings: Settings) -> ScoreResult:
    if not page.success:
        return ScoreResult(0.0, {"parser_failure": 0.0})
    source_chars = sum(not char.isspace() for char in features.embedded_text)
    parsed_chars = sum(not char.isspace() for char in page.text)
    expected_chars = max(source_chars, 80 if features.image_coverage > 0.5 else 25)
    signals: dict[str, float] = {
        "text_coverage": min(1.0, parsed_chars / expected_chars),
        "character_integrity": 1.0 - garbled_ratio(page.text),
        "character_plausibility": character_plausibility(page.text),
        "script_plausibility": script_plausibility(page.text),
    }
    if page.parser_name == "pymupdf":
        signals["text_ink_alignment"] = features.text_ink_alignment
    if features.table_likelihood >= settings.parser_table_likelihood_threshold:
        signals["table_consistency"] = _table_consistency(page)
        if features.previous_page_table_likelihood >= settings.parser_table_likelihood_threshold:
            signals["cross_page_table_continuity"] = 0.0
    if features.image_coverage >= 0.5:
        signals["visual_clarity"] = 1.0 - features.rendered_noise_score
    if page.reported_confidence is not None:
        signals["parser_confidence"] = page.reported_confidence
    if (
        page.parser_name != "pymupdf"
        and source_chars >= 20
        and features.text_ink_alignment >= 0.5
        and character_plausibility(features.embedded_text) >= 0.5
    ):
        source_words, parsed_words = _words(features.embedded_text), _words(page.text)
        signals["parser_agreement"] = (
            len(source_words & parsed_words) / len(source_words | parsed_words)
            if source_words | parsed_words
            else 1.0
        )
    return ScoreResult(score=combine_signals(signals), signals=signals)
