"""Explicit placeholder: no production pipeline exists in Phase 1."""

from pathlib import Path

from eval.baselines.base import ParsedDocument


class UnmessPending:
    name = "unmess"

    def parse(self, path: Path, doc_id: str) -> ParsedDocument:
        raise NotImplementedError("Unmess pipeline is not implemented yet")
