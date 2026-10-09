# ADR 0002: Route each page by observable difficulty

- Status: Accepted
- Date: 2026-10-10

## Context

Using a vision-language model for every page is slow and expensive, while one cheap extractor
cannot reliably handle scans and complex layouts. Documents routinely mix both page types.

## Decision

Compute page features for embedded-text density, image coverage, table likelihood, skew, and
language. Route clean digital pages to PyMuPDF, complex layouts/tables to Docling, and scans,
low-text pages, or failed/low-confidence parses to an Ollama vision model. Record the selected
parser and reasons. Keep all thresholds in typed environment configuration and cover boundary
behavior with tests.

## Consequences

Routing adds orchestration and observability but avoids unnecessary heavy inference. Evaluation
must report both quality and cheap-parser share so efficiency cannot hide quality regressions.
