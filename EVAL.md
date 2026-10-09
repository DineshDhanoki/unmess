# Evaluation contract

Evaluation is built before pipeline internals so implementation choices answer measurable
questions. The harness will run every system on the same generated corpus and write both
machine-readable JSON and a Markdown report to `eval/results/`.

## Dataset

`scripts/make_synthetic_docs.py` will deterministically create labeled clean PDFs,
rotated/noisy scans, receipts, GST-style invoices, merged-cell and multi-row tables,
English/Hindi pages, and tables spanning pages. Ground truth will include expected text,
table cells, and question/answer records pointing to the answering chunk or page. Only
synthetic data is allowed in the repository.

## Systems compared

- Plain PyMuPDF text extraction plus fixed-size chunking.
- Docling-only parsing.
- The complete Unmess routing, scoring, and structure-aware pipeline.

## Metrics

- Table cell-level precision, recall, and F1.
- Character error rate on OCR pages.
- Retrieval Recall@k and mean reciprocal rank.
- Chunk integrity, including the percentage of tables split across chunks.
- Citation accuracy: whether the cited page and bounding box contain the answer.
- Routing efficiency: the share of pages handled by the cheap parser.
- End-to-end and per-page latency, reported with environment context.

## Reproducibility and claims

Reports must include date, dataset version/seed, code revision, hardware where relevant,
dependency versions, model names, configuration, and failures. A missing metric is reported as
missing, never inferred. README figures may only be copied from a committed harness report and
must cite its date and models. The sample report is formatting guidance, not benchmark evidence.

The runnable harness and baselines are Phase 1 deliverables. See `eval/README.md` for its
planned command and output layout.
