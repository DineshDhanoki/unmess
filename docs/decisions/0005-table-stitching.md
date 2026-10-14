# ADR 0005: Conservative rule-based table stitching

- Status: accepted for Phase 3a DEV evaluation
- Date: 2026-10-14

## Context

Page parsers commonly return one table per page even when a logical table spans a page boundary.
Column count alone is unsafe: unrelated adjacent tables often share the same shape and nearly the
same headers. The stitcher must also operate on ordinary `ParsedPage` output, whose block labels
and geometry vary by parser.

## Decision

Use a deterministic rule-based candidate classifier with only three tunable parameters: normalized
header similarity, horizontal geometry tolerance, and page-edge band. Candidates must be on
consecutive pages, have the same column count, begin with a first fragment near the page end, and
have compatible width and offsets. Continuity additionally requires a tolerant repeated header,
an explicit continued caption, or matching normalized table identity. A below-top second fragment
requires matching identity across the intervening content. Conflicting captions or sections,
mid-page termination, and geometry mismatch veto a merge.

On merge, discard only a detected repeated header, preserve a headerless first row as data,
continue row indices, and union page and bounding-box provenance. Store the result as both Markdown
and structured JSON.

## Consequences

The rules are auditable and cheap, and hard negatives constrain false merges. They may miss real
continuations with weak identity or severely distorted geometry. DEV reporting therefore includes
leave-one-pair-out results, category counts, an oracle-input upper bound, and explicit false-merge
counts. A learned stitcher is deferred until real-document evidence justifies the added complexity.
