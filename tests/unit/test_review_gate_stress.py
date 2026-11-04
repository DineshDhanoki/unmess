from pathlib import Path

import pytest

from eval.review_gate_stress import CATEGORIES, accuracy, cases, evaluate, markdown, summarize
from unmess.config import Settings


def test_fixture_categories_have_bad_pages_and_correct_controls() -> None:
    fixtures = cases()
    assert len({case.case_id for case in fixtures}) == len(fixtures) == 36
    assert {case.category for case in fixtures} == set(CATEGORIES)
    for category in CATEGORIES:
        rows = [case for case in fixtures if case.category == category]
        assert len(rows) == 6
        assert sum(case.control for case in rows) == 3
        for case in rows:
            assert (accuracy(case) == 1.0) if case.control else (accuracy(case) < 0.90)
            assert case.parsed.page_number == 1
            assert case.parsed.reported_confidence == 1.0
            assert all(cell.bbox.page == 1 for table in case.parsed.tables for cell in table.cells)
    # Callers can mutate a prediction without modifying its reference or another evaluation run.
    table_case = next(case for case in fixtures if case.reference_tables)
    table_case.parsed.tables[0].cells[0].text = "mutation"
    assert table_case.reference_tables[0].cells[0].text != "mutation"
    assert fixtures != cases()


def test_summary_counts_every_outcome_and_handles_undefined_rates() -> None:
    rows = [
        {"quality_score": 0.2, "accuracy": 0.2, "bad": True, "flagged": True},
        {"quality_score": 0.9, "accuracy": 0.2, "bad": True, "flagged": False},
        {"quality_score": 0.2, "accuracy": 1.0, "bad": False, "flagged": True},
        {"quality_score": 0.9, "accuracy": 1.0, "bad": False, "flagged": False},
    ]
    result = summarize(rows, seed=123)
    assert [
        result[key]
        for key in ("true_positive", "false_positive", "false_negative", "true_negative")
    ] == [1, 1, 1, 1]
    assert result["precision"] == result["recall"] == 0.5
    assert summarize(rows, seed=123) == result
    for interval in result["ci95"].values():
        assert 0 <= interval["lower"] <= 0.5 <= interval["upper"] <= 1
        assert 0 < interval["samples"] <= 2000
    empty_denominator = summarize([rows[-1]], seed=123)
    assert empty_denominator["precision"] is None
    assert empty_denominator["recall"] is None
    assert empty_denominator["ci95"]["precision"]["samples"] == 0


def test_evaluation_runs_offline_without_loading_corpus_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_read(*args: object, **kwargs: object) -> str:
        raise AssertionError("the synthetic gate evaluation must not read corpus files")

    settings = Settings()
    monkeypatch.setattr(Path, "open", no_read)
    report = evaluate(settings)
    assert report["split"] == "dev"
    assert report["overall"]["pages"] == 36
    assert report["overall"]["bad_pages"] == 18
    assert report["failures"] == [
        row["case_id"] for row in report["cases"] if row["bad"] != row["flagged"]
    ]
    rendered = markdown(report)
    assert all(case_id in rendered for case_id in report["failures"])
    assert all(category in rendered for category in CATEGORIES)
