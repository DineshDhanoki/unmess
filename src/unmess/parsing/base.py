"""Parser contract shared by adapters, routing, and workers."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from unmess.models import BBox, Block, Table


@dataclass(frozen=True)
class ParserAttempt:
    parser: str
    reason: str
    succeeded: bool
    quality_score: float
    error: str | None = None
    duration_s: float = 0.0
    cache_hit: bool = False


@dataclass
class ParsedPage:
    page_number: int
    parser_name: str
    text: str = ""
    blocks: list[Block] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    bboxes: list[BBox] = field(default_factory=list)
    parse_time_s: float = 0.0
    success: bool = True
    error: str | None = None
    reported_confidence: float | None = None
    quality_score: float = 0.0
    quality_signals: dict[str, float] = field(default_factory=dict)
    source_features: dict[str, float | str] = field(default_factory=dict)
    review_reasons: list[str] = field(default_factory=list)
    route_reason: str = ""
    attempts: list[ParserAttempt] = field(default_factory=list)
    previous_attempt: "ParsedPage | None" = None
    cache_hit: bool = False

    @classmethod
    def failed(
        cls, page_number: int, parser_name: str, error: str, parse_time_s: float = 0.0
    ) -> "ParsedPage":
        return cls(
            page_number=page_number,
            parser_name=parser_name,
            parse_time_s=parse_time_s,
            success=False,
            error=error,
        )


class Parser(Protocol):
    name: str

    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage: ...


class ParserUnavailable(RuntimeError):
    """Raised when an optional parser dependency is not installed."""


def normalized_bbox(
    page_number: int, rect: tuple[float, float, float, float], width: float, height: float
) -> BBox:
    """Convert top-left PDF coordinates to the shared 0-1 geometry."""
    x0, y0, x1, y1 = rect
    return BBox(
        page=page_number,
        x0=max(0.0, min(1.0, x0 / width)),
        y0=max(0.0, min(1.0, y0 / height)),
        x1=max(0.0, min(1.0, x1 / width)),
        y1=max(0.0, min(1.0, y1 / height)),
    )
