from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval_phase3.evaluate_stitching_dev import _example, _oracle_pages, _system_result
from eval_phase3.generate_dataset import generate

REQUIRED_HARD_NEGATIVES = {
    "unrelated_same_columns",
    "misleading_repeated_header",
    "midpage_then_different",
    "continuation_after_figure",
}


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


def test_phase3_dev_hard_negatives_pin_categories_labels_and_cell_content(
    tmp_path: Path,
) -> None:
    output = tmp_path / "dataset"
    manifest = generate(output)
    dev_items = [item for item in manifest["documents"] if item["split"] == "dev"]
    category_counts = Counter(str(item["category"]) for item in dev_items)

    assert category_counts.keys() >= REQUIRED_HARD_NEGATIVES
    assert all(category_counts[category] >= 1 for category in REQUIRED_HARD_NEGATIVES)

    for item in dev_items:
        if item["category"] not in REQUIRED_HARD_NEGATIVES:
            continue
        truth = json.loads((output / item["ground_truth"]).read_text(encoding="utf-8"))
        assert truth["stitch_pair"]["should_stitch"] is False
        assert truth["stitch_pair"]["reason"].strip()
        tables = [
            element
            for page in truth["pages"]
            for element in page["elements"]
            if element["kind"] == "table"
        ]
        assert [table["table_id"] for table in tables] == truth["stitch_pair"]["table_ids"]
        assert len(tables) == 2
        assert all(cell["text"].strip() for table in tables for cell in table["cells"])

    headerless_item = next(
        item for item in dev_items if item["category"] == "continuation_without_header"
    )
    headerless_truth = json.loads(
        (output / headerless_item["ground_truth"]).read_text(encoding="utf-8")
    )
    second_page_table = next(
        element
        for element in headerless_truth["pages"][1]["elements"]
        if element["kind"] == "table"
    )
    assert headerless_truth["stitch_pair"]["should_stitch"] is True
    assert second_page_table["header_rows"] == []
    assert all(cell["text"].strip() for cell in second_page_table["cells"])


def test_phase3_dev_runner_reports_each_hard_negative_without_false_merges(
    tmp_path: Path,
) -> None:
    output = tmp_path / "dataset"
    manifest = generate(output)
    dev_items = [item for item in manifest["documents"] if item["split"] == "dev"]
    examples = []
    for item in dev_items:
        truth = json.loads((output / item["ground_truth"]).read_text(encoding="utf-8"))
        examples.append(_example(item, truth, _oracle_pages(truth)))

    result = _system_result("oracle regression", examples)

    assert result["categories"].keys() >= REQUIRED_HARD_NEGATIVES
    for category in REQUIRED_HARD_NEGATIVES:
        counts = result["categories"][category]
        assert counts["false_positive"] == 0
        assert counts["true_negative"] > 0
