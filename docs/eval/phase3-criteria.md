# Phase 3 evaluation criteria

These criteria are registered before inspecting any Phase 3 DEV result. Phase 3a evaluates
structure-aware chunking, table stitching, and citation provenance only. Retrieval and answer
quality remain Phase 3b work.

## Phase 3a DEV criteria

All failures remain in their applicable denominators. Results must include overall counts and
category-level results for positive continuations and every hard-negative category.

1. **Chunk integrity:** PASS only if Unmess splits zero reference tables across multiple chunks
   (`table_split_rate = 0.0`) and its split rate is no worse than the naive fixed-size baseline.
   Every emitted table chunk must contain both Markdown and structured JSON representations.
2. **Citation accuracy:** PASS only if at least 95% of evaluated chunks cite every reference
   page and their normalized source boxes intersect the reference source regions. A chunk with
   a missing page, missing box, or non-intersecting box is incorrect.
3. **Spanning-table reconstruction:** PASS only if stitched table cell F1 is at least `0.80`,
   is strictly higher than the naive fixed-size baseline, and improves by at least `0.15`
   absolute over the same Unmess table representation before stitching. Report all three point
   estimates and their document counts.
4. **False merges:** PASS only if the stitching false-merge rate is `0.0` on hard negatives.
   The denominator includes unrelated adjacent-page tables with equal column counts, missing or
   misleading repeated headers, a table ending mid-page followed by a different table, and a
   possible continuation separated by a figure. Column count alone is never sufficient evidence
   for stitching.

Where Unmess loses to the naive baseline, the report must identify the category and metric. DEV
tuning may change Phase 3-only code and configuration, with every attempted change recorded in
the Phase 3a tuning log. It may not alter any `freeze-v1` file.

## Test protocol

The Phase 3 test split stays sealed during development: its ground truth and evaluation numbers
must not be read. After DEV work is approved, Phase 3 will receive its own `freeze-v2` covering
its code, configuration, dataset, criteria, runner, and report generator. Exactly one Phase 3
test run will occur after that freeze, before any Phase 3 test numbers are read.

The deferred Phase 2 test remains bound to `freeze-v1` and will be run from a separate worktree
checked out at that tag. Phase 3 commits on `main` do not modify or supersede the v1 freeze.
