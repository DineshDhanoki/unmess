"""Evaluation adapter contract, independent of the future production pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from unmess.models import Chunk, Table


@dataclass
class ParsedDocument:
    page_texts: list[str]
    chunks: list[Chunk]
    tables: list[Table] = field(default_factory=list)
    page_durations_s: list[float] = field(default_factory=list)
    parsers: list[str] = field(default_factory=list)


class PipelineAdapter(Protocol):
    name: str

    def parse(self, path: Path, doc_id: str) -> ParsedDocument: ...
