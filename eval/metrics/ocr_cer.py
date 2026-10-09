"""Character error rate on exact expected text."""


def character_error_rate(expected: str, predicted: str) -> float:
    """Levenshtein distance / reference length; empty reference is defined explicitly."""
    if not expected:
        return 0.0 if not predicted else 1.0
    previous = list(range(len(predicted) + 1))
    for i, source_char in enumerate(expected, 1):
        current = [i]
        for j, target_char in enumerate(predicted, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (source_char != target_char),
                )
            )
        previous = current
    return previous[-1] / len(expected)
