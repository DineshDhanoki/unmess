# ADR 0001: Wrap, do not rebuild, document parsers

- Status: Accepted
- Date: 2026-10-10

## Context

Docling, Marker, and PyMuPDF already solve substantial parts of PDF interpretation. Rebuilding
their extraction and OCR work would dilute effort from Unmess's differentiators and make
quality harder to compare.

## Decision

Define a small parser interface and implement adapters for mature parsers. Preserve their
native confidence and layout metadata when available. Unmess owns routing, normalized models,
quality assessment, provenance, chunking, retrieval, and evaluation—not parser internals.

## Consequences

Parser-specific dependencies are optional and replaceable. Upstream differences require
normalization and compatibility tests. A new parser is admitted through the interface and must
be evaluated on the shared corpus before it becomes a default route.
