"""File, page, and chunk hashing for incremental re-ingestion."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from unmess.chunking.schema import ChunkRecord


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_page(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def hash_chunk(chunk: ChunkRecord) -> str:
    return chunk.content_hash


@dataclass(frozen=True)
class IngestPlan:
    unchanged: bool
    changed_pages: tuple[int, ...]
    remove_chunk_ids: tuple[str, ...]


@dataclass
class _DocumentState:
    file_hash: str
    page_hashes: dict[int, str]
    chunks: dict[str, ChunkRecord] = field(default_factory=dict)


class DedupeStore:
    def __init__(self) -> None:
        self._documents: dict[str, _DocumentState] = {}

    def plan(self, document_id: str, file_hash: str, page_hashes: dict[int, str]) -> IngestPlan:
        previous = self._documents.get(document_id)
        if previous is None:
            return IngestPlan(False, tuple(sorted(page_hashes)), ())
        if previous.file_hash == file_hash and previous.page_hashes == page_hashes:
            return IngestPlan(True, (), ())
        page_numbers = set(previous.page_hashes) | set(page_hashes)
        changed = tuple(
            sorted(
                page
                for page in page_numbers
                if previous.page_hashes.get(page) != page_hashes.get(page)
            )
        )
        removals = tuple(
            sorted(
                chunk_id
                for chunk_id, chunk in previous.chunks.items()
                if set(chunk.page_numbers).intersection(changed)
            )
        )
        return IngestPlan(False, changed, removals)

    def commit(
        self,
        document_id: str,
        file_hash: str,
        page_hashes: dict[int, str],
        chunks: list[ChunkRecord],
        plan: IngestPlan,
    ) -> None:
        if plan.unchanged:
            return
        previous = self._documents.get(document_id)
        retained = {} if previous is None else dict(previous.chunks)
        for chunk_id in plan.remove_chunk_ids:
            retained.pop(chunk_id, None)
        retained.update({chunk.chunk_id: chunk for chunk in chunks})
        self._documents[document_id] = _DocumentState(file_hash, dict(page_hashes), retained)

    def chunks(self, document_id: str) -> tuple[ChunkRecord, ...]:
        state = self._documents.get(document_id)
        if state is None:
            return ()
        return tuple(state.chunks[key] for key in sorted(state.chunks))
