"""Latency measures."""

from collections.abc import Sequence


def latency_per_page(page_durations_s: Sequence[float]) -> float | None:
    if any(value < 0 for value in page_durations_s):
        raise ValueError("durations must be nonnegative")
    return sum(page_durations_s) / len(page_durations_s) if page_durations_s else None
