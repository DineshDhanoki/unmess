"""Share of pages handled by the low-cost extractor."""

from collections.abc import Sequence


def cheap_parser_share(parsers: Sequence[str], cheap_parser: str = "pymupdf") -> float | None:
    return sum(parser == cheap_parser for parser in parsers) / len(parsers) if parsers else None
