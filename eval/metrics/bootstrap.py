"""Fixed-seed document bootstrap confidence intervals."""

import random
import statistics
from typing import Any


def document_bootstrap_ci(
    rows: list[dict[str, Any]],
    metric: str,
    *,
    seed: int,
    samples: int = 2000,
) -> dict[str, float | int | None]:
    """Percentile 95% interval after resampling whole document rows."""
    if not rows or samples < 1:
        raise ValueError("bootstrap requires documents and positive sample count")
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(samples):
        selected = [rows[rng.randrange(len(rows))] for _ in rows]
        values = [float(row[metric]) for row in selected if row[metric] is not None]
        if values:
            estimates.append(statistics.mean(values))
    if not estimates:
        return {"lower": None, "upper": None, "samples": 0, "seed": seed}
    estimates.sort()
    lower_index = int(0.025 * (len(estimates) - 1))
    upper_index = int(0.975 * (len(estimates) - 1))
    return {
        "lower": estimates[lower_index],
        "upper": estimates[upper_index],
        "samples": len(estimates),
        "seed": seed,
    }
