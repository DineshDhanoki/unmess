# Phase 3a DEV stitching evaluation

Ground truth was used for scoring only. Docling and router inputs are `ParsedPage` output from the real pipeline. The oracle-input row is an upper bound built from ground-truth cells.

| Input | Pairs | Extracted pairs | LOPO pair F1 | False merges | Before cell F1 | After cell F1 | Table splits | Citation accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| oracle input | 29 | 29 | 1.000 | 0/17 | 0.750 | 1.000 | 0/46 | 46/46 (1.000) |
| Docling ParsedPage | 29 | 29 | 1.000 | 0/17 | 0.750 | 0.913 | 0/46 | 46/50 (0.920) |
| Unmess router ParsedPage | 29 | 29 | 1.000 | 0/17 | 0.750 | 0.913 | 0/46 | 46/50 (0.920) |

The naive fixed-size baseline emits no structured cross-page table and therefore has pair F1 and spanning-table cell F1 of 0.000. Its 600-token windows are evaluated separately for chunk integrity.

LOPO chooses among the preregistered stitcher's three parameters only: header similarity, geometry tolerance, and page-edge band. Full counts, category breakdowns, routing shares, failures, and selected configurations are in `stitching-dev.json`.

## Preregistered criteria

- PASS — chunk integrity: 0/46 reference tables split; naive fixed-size rate 0.000.
- FAIL — citation accuracy: 46/50 (0.920).
- PASS — spanning-table reconstruction: before 0.750, after 0.913, absolute improvement 0.163, naive 0.000.
- PASS — false merges: 0/17 hard negatives; LOPO pair F1 1.000.

## Category counts for Unmess router input

| Category | TP | FP | FN | TN |
|---|---:|---:|---:|---:|
| continuation_across_figure | 2 | 0 | 0 | 0 |
| continuation_after_figure | 0 | 0 | 0 | 2 |
| continuation_repeated_header | 6 | 0 | 0 | 0 |
| continuation_without_header | 4 | 0 | 0 | 0 |
| geometry_mismatch | 0 | 0 | 0 | 4 |
| midpage_then_different | 0 | 0 | 0 | 3 |
| misleading_repeated_header | 0 | 0 | 0 | 4 |
| unrelated_same_columns | 0 | 0 | 0 | 4 |

## Where Unmess loses

Citation accuracy is below the preregistered threshold. Docling classified four synthetic figure regions as additional table fragments; those chunks do not intersect a reference table. Cell reconstruction also remains below the oracle-input upper bound because parser-visible cells include grouping errors around running page furniture. The router selected Docling for all 58 pages, so its result is identical to the Docling row on this corpus.

Real-document validation: pending.
