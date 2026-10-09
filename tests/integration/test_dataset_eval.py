"""Committed corpus, regeneration, and baseline runner contracts."""

import hashlib
import json
from pathlib import Path

import pymupdf

from eval.run_eval import run
from scripts.make_synthetic_docs import CATEGORIES, SEED, build_document
from unmess.models import GroundTruth

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "eval/datasets"


def test_dataset_manifest_ground_truth_and_size() -> None:
    manifest = json.loads((DATASET / "MANIFEST.json").read_text())
    assert manifest["seed"] == SEED
    assert len(manifest["documents"]) == 56
    assert (
        sum((DATASET / item["pdf"]).stat().st_size for item in manifest["documents"]) < 25_000_000
    )
    for category in CATEGORIES:
        truths = [
            GroundTruth.model_validate_json((DATASET / item["ground_truth"]).read_text())
            for item in manifest["documents"]
            if item["document_id"].startswith(f"synthetic-{category}-")
        ]
        assert len(truths) == 8
        assert {truth.split for truth in truths} == {"dev", "test"}
        assert sum(truth.split == "dev" for truth in truths) == 4
        assert all(3 <= len(truth.questions) <= 5 for truth in truths)


def test_regenerate_one_pdf_byte_for_byte() -> None:
    font = DATASET / ".font-cache/NotoSansDevanagari.ttf"
    raw, truth = build_document("bilingual", 7, font)
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
    result = run(DATASET)
    baseline = result["systems"]["pymupdf_fixed"]
    assert baseline["dev"]["status"] == "partial_failure"
    assert baseline["dev"]["summary"]["overall"]["failed_pages"] > 0
    assert baseline["dev"]["summary"]["overall"]["documents"] == 28
    assert baseline["test"] is None
    assert result["systems"]["unmess_parsing"]["dev"]["summary"]["overall"]["documents"] == 28
    assert result["systems"]["unmess_parsing"]["test"] is None
