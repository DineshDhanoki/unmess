"""Phase 3 chunk records without changing the frozen Phase 2 models."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal

from unmess.models import BBox

ChunkKind = Literal["text", "table"]


def content_hash(value: str | bytes) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class StructuredTable:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    row_indices: tuple[int, ...]
    source_table_ids: tuple[str, ...]

    def as_json(self) -> str:
        return json.dumps(
            {
                "columns": self.columns,
                "rows": self.rows,
                "row_indices": self.row_indices,
                "source_table_ids": self.source_table_ids,
            },
            ensure_ascii=False,
            sort_keys=True,
        )


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    kind: ChunkKind
    markdown: str
    file_hash: str
    page_hashes: tuple[str, ...]
    page_numbers: tuple[int, ...]
    bboxes: tuple[BBox, ...]
    section_path: tuple[str, ...]
    parser_names: tuple[str, ...]
    content_hash: str
    structured_table: StructuredTable | None = None
    context: str | None = None
    block_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.page_numbers:
            raise ValueError("chunk must cite at least one page")
        if len(self.page_hashes) != len(self.page_numbers):
            raise ValueError("page hashes must align with page numbers")
        if any(box.page not in self.page_numbers for box in self.bboxes):
            raise ValueError("bbox page must belong to chunk")
        if self.kind == "table" and self.structured_table is None:
            raise ValueError("table chunks require structured JSON data")
        if self.kind == "text" and self.structured_table is not None:
            raise ValueError("text chunks cannot carry a structured table")
