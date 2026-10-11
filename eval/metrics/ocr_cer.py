"""Character and word error rates on exact expected text."""

from collections.abc import Sequence


def _distance(expected: Sequence[str], predicted: Sequence[str]) -> int:
    previous = list(range(len(predicted) + 1))
    for i, source in enumerate(expected, 1):
        current = [i]
        for j, target in enumerate(predicted, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (source != target))
            )
        previous = current
    return previous[-1]


def character_error_rate(expected: str, predicted: str) -> float:
    """Levenshtein distance / reference length; empty reference is defined explicitly."""
    if not expected:
        return 0.0 if not predicted else 1.0
    return _distance(expected, predicted) / len(expected)


def word_error_rate(expected: str, predicted: str) -> float:
    """Whitespace-token Levenshtein distance / reference token count."""
    reference, hypothesis = expected.split(), predicted.split()
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return _distance(reference, hypothesis) / len(reference)
