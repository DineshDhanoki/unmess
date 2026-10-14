# Phase 3a tuning log

## 2026-10-14 — preregistered implementation, before DEV results

- Kept the criteria in `docs/eval/phase3-criteria.md` unchanged after expanding each split to 12
  positive and 17 hard-negative pairs.
- Fixed the stitcher to three parameters: header similarity, geometry tolerance, and page-edge
  band. Initial defaults are 0.72, 0.08 normalized page width, and 0.20 normalized page height.
- Defined deterministic vetoes for nonconsecutive pages, unequal column count, mid-page endings,
  horizontal geometry mismatch, and incompatible table identity.
- Allowed a continuation after intervening content only when table identity remains compatible;
  the intervening figure or text is not itself positive evidence.
- Defined the DEV robustness check as leave-one-pair-out selection over a small fixed grid for the
  same three parameters. Ground-truth cells are used only for scoring and the labeled oracle-input
  upper-bound row.

No Phase 3 DEV result had been produced when these choices were recorded.

## 2026-10-14 — infrastructure note

- The first real-pipeline DEV attempt aborted in Apple's Metal command-buffer implementation
  before writing results. The stitcher and criteria were unchanged.
- The identical evaluator is rerun with Docling's documented `DOCLING_DEVICE=cpu` setting; the
  selected device is recorded in the raw result file.

## 2026-10-14 — DEV iteration 1

- Real Docling and router input produced pair F1 0.800 with 8/12 continuations found and 0/17
  false merges. The oracle-input row was 12/12 and 0/17.
- Two misses followed an intervening figure that Docling represented as an additional one-column
  table. Changed candidate enumeration to examine all table-shaped candidates on the immediately
  following page while retaining every existing continuity requirement and veto.
- Two misses had an extra column populated only in the leading row, introduced by parser grouping
  around running page furniture. Added a generic sparse-leading-column normalization before column
  compatibility is tested. No threshold or parameter changed.

## 2026-10-14 — DEV iteration 2 (final)

- Docling and router inputs both reached 12/12 true continuations and 0/17 false merges; LOPO chose
  the unchanged default configuration for every held-out pair.
- Stopped tuning. Citation accuracy remained 46/50 because Docling emitted four figure regions as
  table fragments. Suppressing one-cell tables could hide those errors but would also discard valid
  small tables without generic evidence, so the failure is retained and reported.
