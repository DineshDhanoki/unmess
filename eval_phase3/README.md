# Phase 3 synthetic dataset

This directory is independent of the frozen Phase 2 dataset. Regenerate it with:

```bash
uv run python -m eval_phase3.generate_dataset
```

All content is visibly synthetic and fictional. DEV ground truth may be used during Phase 3
development. The test ground-truth files are sealed until a future `freeze-v2` and its single
test run. Manifest metadata may be inspected without opening test ground truth.

The corpus pairs DEV and test variants for positive cross-page continuations and hard negatives:
equal-column unrelated tables, misleading repeated headers, a table ending mid-page before a
different table, and a possible continuation interrupted by a figure.
