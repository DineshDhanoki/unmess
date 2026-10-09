"""Machine-readable decisions for human review."""

from unmess.config import Settings
from unmess.models import QualityReport
from unmess.parsing.base import ParsedPage
from unmess.parsing.page_features import PageFeatures, garbled_ratio


def review_gate(
    document_id: str, page: ParsedPage, features: PageFeatures, settings: Settings
) -> QualityReport:
    reasons: list[str] = []
    if not page.success:
        reasons.append("parser_failed")
    if page.quality_score < settings.quality_review_threshold:
        reasons.append("below_quality_threshold")
    if not page.text.strip():
        reasons.append("empty_text")
    if features.table_likelihood >= settings.parser_table_likelihood_threshold and not page.tables:
        reasons.append("table_not_recovered")
    if garbled_ratio(page.text) > settings.parser_garbled_ratio_threshold:
        reasons.append("garbled_text")
    return QualityReport(
        document_id=document_id,
        page_number=page.page_number,
        score=page.quality_score,
        reasons=reasons,
        flagged_for_review=bool(reasons),
    )
