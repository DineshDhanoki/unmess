"""Question-level retrieval measures."""

from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")


def recall_at_k(ranked: Sequence[T], relevant: Callable[[T], bool], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    return float(any(relevant(item) for item in ranked[:k]))


def reciprocal_rank(ranked: Sequence[T], relevant: Callable[[T], bool]) -> float:
    return next((1.0 / index for index, item in enumerate(ranked, 1) if relevant(item)), 0.0)
