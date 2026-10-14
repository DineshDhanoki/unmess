from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval_phase3.generate_dataset import generate


def _counts(manifest: dict[str, Any], split: str) -> tuple[int, int, int]:
    documents = [item for item in manifest["documents"] if item["split"] == split]
    positives = sum(int(item["positive_stitch_pairs"]) for item in documents)
    negatives = sum(int(item["negative_stitch_pairs"]) for item in documents)
    return len(documents), positives, negatives


def test_phase3_generator_has_required_pairs_and_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_manifest = generate(first)
    second_manifest = generate(second)

    assert _counts(first_manifest, "dev") == (29, 12, 17)
    assert _counts(first_manifest, "test") == (29, 12, 17)
    assert first_manifest == second_manifest
    assert json.loads((first / "MANIFEST.json").read_text(encoding="utf-8")) == first_manifest
    assert len(list((first / "pdf").glob("*.pdf"))) == 58
    assert len(list((first / "ground_truth").glob("*.json"))) == 58
