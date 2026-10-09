"""Score/accuracy calibration on labeled dev pages."""

import math
import statistics
from collections.abc import Sequence


def _ranks(values: Sequence[float]) -> list[float]:
    result = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=lambda index: values[index])
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in ordered[start:end]:
            result[index] = rank
        start = end
    return result


def spearman(scores: Sequence[float], accuracies: Sequence[float]) -> float | None:
    if len(scores) != len(accuracies):
        raise ValueError("score and accuracy counts differ")
    if len(scores) < 2:
        return None
    left, right = _ranks(scores), _ranks(accuracies)
    left_mean, right_mean = statistics.mean(left), statistics.mean(right)
    covariance = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True))
    left_var = sum((value - left_mean) ** 2 for value in left)
    right_var = sum((value - right_mean) ** 2 for value in right)
    return covariance / math.sqrt(left_var * right_var) if left_var and right_var else None


def score_buckets(
    scores: Sequence[float], accuracies: Sequence[float]
) -> dict[str, dict[str, float | int | None]]:
    if len(scores) != len(accuracies):
        raise ValueError("score and accuracy counts differ")
    buckets: dict[str, list[float]] = {
        "0.00-0.25": [],
        "0.25-0.50": [],
        "0.50-0.75": [],
        "0.75-1.00": [],
    }
    for score, accuracy in zip(scores, accuracies, strict=True):
        if not 0 <= score <= 1 or not 0 <= accuracy <= 1:
            raise ValueError("scores and accuracies must be within 0-1")
        index = min(3, int(score * 4))
        key = list(buckets)[index]
        buckets[key].append(accuracy)
    return {
        key: {
            "pages": len(values),
            "mean_page_accuracy": statistics.mean(values) if values else None,
        }
        for key, values in buckets.items()
    }
