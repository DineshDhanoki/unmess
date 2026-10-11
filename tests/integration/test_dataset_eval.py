"""Committed corpus, regeneration, and baseline runner contracts."""

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from eval.baselines.plain_pymupdf import PlainPyMuPDF
from eval.run_eval import _run_adapter, _validate_manifest
from scripts.make_synthetic_docs import CATEGORIES, EXPANDED_COUNTS, SEED, build_document
from unmess.models import GroundTruth

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "eval/datasets"


def test_dataset_manifest_ground_truth_and_size() -> None:
    manifest = json.loads((DATASET / "MANIFEST.json").read_text())
    assert manifest["seed"] == SEED
    assert len(manifest["documents"]) == 86
    assert sum(path.stat().st_size for path in DATASET.rglob("*") if path.is_file()) < 25_000_000
    for category in CATEGORIES:
        truths = [
            GroundTruth.model_validate_json((DATASET / item["ground_truth"]).read_text())
            for item in manifest["documents"]
            if item["document_id"].startswith(f"synthetic-{category}-") and item["split"] == "dev"
        ]
        assert len(truths) == EXPANDED_COUNTS.get(category, 8) // 2
        assert all(truth.split == "dev" for truth in truths)
        assert all(3 <= len(truth.questions) <= 5 for truth in truths)


@pytest.mark.parametrize(
    ("category", "index"),
    [("bilingual", 8), ("broken_text_layer", 0), ("fake_text_layer_scan", 0), ("mixed_pages", 0)],
)
def test_regenerate_one_pdf_byte_for_byte(category: str, index: int) -> None:
    font = DATASET / ".font-cache/NotoSansDevanagari.ttf"
    raw, truth = build_document(category, index, font)
    pdf = DATASET / truth.source_file
    assert raw == pdf.read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as document:
        assert document.metadata["producer"] == "Unmess synthetic generator"
        assert document.metadata["creationDate"] == "D:20000101000000+00'00'"


def test_all_pdf_hashes_and_baseline_run() -> None:
    manifest = json.loads((DATASET / "MANIFEST.json").read_text())
    assert all(
        hashlib.sha256((DATASET / item["pdf"]).read_bytes()).hexdigest() == item["sha256"]
        for item in manifest["documents"]
    )
    truths, _ = _validate_manifest(DATASET, "dev")
    baseline = _run_adapter(PlainPyMuPDF(), truths, DATASET, "dev")
    assert baseline["status"] == "partial_failure"
    assert baseline["summary"]["overall"]["failed_pages"] > 0
    assert baseline["summary"]["overall"]["documents"] == 43


def test_dev_manifest_validation_never_reads_test_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = json.loads((DATASET / "MANIFEST.json").read_text())
    forbidden = {
        DATASET / item["ground_truth"] for item in manifest["documents"] if item["split"] == "test"
    }
    original = Path.read_text

    def checked_read(path: Path, encoding: str | None = None, errors: str | None = None) -> str:
        assert path not in forbidden
        return original(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", checked_read)
    truths, _ = _validate_manifest(DATASET, "dev")
    assert len(truths) == 43
