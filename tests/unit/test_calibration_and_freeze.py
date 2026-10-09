import pytest

from eval.metrics.calibration import score_buckets, spearman
from eval.run_eval import assert_test_ready


def test_spearman_and_buckets() -> None:
    assert spearman([0.1, 0.5, 0.9], [0.2, 0.6, 1.0]) == pytest.approx(1)
    assert spearman([0.5, 0.5], [0.2, 0.8]) is None
    buckets = score_buckets([0.0, 0.6, 1.0], [0.1, 0.5, 0.9])
    assert buckets["0.00-0.25"] == {"pages": 1, "mean_page_accuracy": 0.1}
    assert buckets["0.75-1.00"] == {"pages": 1, "mean_page_accuracy": 0.9}


def test_test_split_refuses_uncommitted_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eval.run_eval._freeze_commit", lambda: None)
    with pytest.raises(RuntimeError, match="not committed"):
        assert_test_ready()
