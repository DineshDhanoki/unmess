"""Transparent page confidence with missing-signal weight renormalization."""

import re
from dataclasses import dataclass

from unmess.config import Settings
from unmess.parsing.base import ParsedPage
from unmess.parsing.page_features import PageFeatures, garbled_ratio

WEIGHTS = {
    "text_coverage": 0.35,
    "character_integrity": 0.25,
    "table_consistency": 0.20,
    "parser_confidence": 0.10,
    "parser_agreement": 0.10,
}


@dataclass(frozen=True)
class ScoreResult:
    score: float
    signals: dict[str, float]


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
    }
    if features.table_likelihood >= settings.parser_table_likelihood_threshold:
        signals["table_consistency"] = _table_consistency(page)
    if page.reported_confidence is not None:
        signals["parser_confidence"] = page.reported_confidence
    if page.parser_name != "pymupdf" and source_chars >= 20:
        source_words, parsed_words = _words(features.embedded_text), _words(page.text)
        signals["parser_agreement"] = (
            len(source_words & parsed_words) / len(source_words | parsed_words)
            if source_words | parsed_words
            else 1.0
        )
    weight = sum(WEIGHTS[name] for name in signals)
    return ScoreResult(
        score=sum(value * WEIGHTS[name] for name, value in signals.items()) / weight,
        signals=signals,
    )
