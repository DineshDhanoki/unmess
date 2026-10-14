# Phase 3 synthetic dataset

This directory is independent of the frozen Phase 2 dataset. Regenerate it with:

```bash
uv run python -m eval_phase3.generate_dataset
```

All content is visibly synthetic and fictional. DEV ground truth may be used during Phase 3
development. The test ground-truth files are sealed until a future `freeze-v2` and its single
test run. Manifest metadata may be inspected without opening test ground truth.

Each split has 12 positive and 17 hard-negative stitch pairs. Variants cover exact and noisy
repeated headers, headerless continuations, optional continued captions, running headers and
footers, figures between true continuations, equal-column unrelated tables with near-identical
headers, geometry mismatches, section changes after figures, and a table ending mid-page before a
different table.
