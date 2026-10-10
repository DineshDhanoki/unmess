import pytest

from eval.metrics.calibration import score_buckets, spearman
from eval.run_eval import _calibration, assert_test_ready


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


def test_calibration_excludes_failed_pages() -> None:
    result = _calibration(
        [
            {
                "quality_scores": [0.2, 0.5, 0.9],
                "page_accuracy": [0.0, 0.4, 0.8],
                "page_success": [False, True, True],
                "failed_pages": 1,
            }
        ]
    )
    assert result["pages"] == 2
    assert result["failed_pages_excluded"] == 1
    assert result["spearman_rho"] == pytest.approx(1.0)
    assert result["score_buckets"]["0.00-0.25"]["pages"] == 0


def test_test_split_refuses_superseded_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "eval.run_eval._freeze_commit",
        lambda: "caa7f35c2f46777eba1a690e0292dac1ea04fe39",
    )
    with pytest.raises(RuntimeError, match="superseded"):
        assert_test_ready()


def test_test_split_refuses_unavailable_route(monkeypatch: pytest.MonkeyPatch) -> None:
    from subprocess import CompletedProcess

    monkeypatch.setattr("eval.run_eval._freeze_commit", lambda: "new-freeze-commit")
    monkeypatch.setattr(
        "eval.run_eval._git",
        lambda _args: CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        "eval.run_eval.run_preflight",
        lambda _settings: {"pymupdf_parse": "ok", "docling_parse": "ok"},
    )
    with pytest.raises(RuntimeError, match="unavailable vlm"):
        assert_test_ready()
