# Unmess Phase 2 parsing evaluation

> **SUPERSEDED — invalid backend-availability run.** Docling's optional package/model
> artifacts were unavailable and Ollama was unreachable. Failures were counted, but these
> test metrics do not evaluate the routing design. The freeze commit was
> `caa7f35c2f46777eba1a690e0292dac1ea04fe39`. No routing or gate threshold was
> changed after inspecting this test run. This file is retained for audit only; a new
> test run requires a successful preflight, dev-only tuning, and a new approved freeze.

Run: 2026-10-09T22:55:11.125481+00:00 | source commit `9df4d5dde634f2d82fe70b846916d46af829ce1d` | freeze commit `caa7f35c2f46777eba1a690e0292dac1ea04fe39`
Working tree dirty: False; dataset: 56 PDFs, 1374226 PDF bytes
Vision model: `qwen2.5vl`; prompt: `phase2-v1`
Python 3.11.15; platform macOS-26.6.2-arm64-arm-64bit; libraries: pymupdf 1.28.2, reportlab 4.5.1, pillow 12.3.0, pydantic 2.14.0
Retrieval metrics: n/a until Phase 3. Dev is for tuning; test is evaluated only after freeze.

Frozen threshold values: `{"parser_complex_layout_threshold": 0.9, "parser_garbled_ratio_threshold": 0.1, "parser_image_coverage_threshold": 0.7, "parser_max_skew_degrees": 3.0, "parser_scan_likelihood_threshold": 0.6, "parser_table_likelihood_threshold": 0.55, "parser_text_density_threshold": 0.12, "quality_review_threshold": 0.7}`

## Test results

| System | Group | Documents | Pages | Failed pages | table_f1 | ocr_cer | cheap_parser_share | latency_per_page_s | failed_page_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | overall:overall | 28 | 32 | 4 | 0.0000 | 1.0000 | 1.0000 | 0.0012 | 0.1429 |
| pymupdf_fixed | category:bilingual | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:clean | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:gst_invoice | 4 | 4 | 0 | 0.0000 | n/a | 1.0000 | 0.0017 | 0.0000 |
| pymupdf_fixed | category:merged_table | 4 | 4 | 0 | 0.0000 | n/a | 1.0000 | 0.0018 | 0.0000 |
| pymupdf_fixed | category:receipt | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | category:spanning_table | 4 | 8 | 0 | 0.0000 | n/a | 1.0000 | 0.0012 | 0.0000 |
| pymupdf_fixed | language:en | 24 | 28 | 4 | 0.0000 | 1.0000 | 1.0000 | 0.0012 | 0.1667 |
| pymupdf_fixed | language:hi | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:not_scan | 24 | 28 | 0 | 0.0000 | n/a | 1.0000 | 0.0013 | 0.0000 |
| docling_only | overall:overall | 28 | 32 | 32 | 0.0000 | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | category:bilingual | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:clean | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:gst_invoice | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:merged_table | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:receipt | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | category:spanning_table | 4 | 8 | 8 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | language:en | 24 | 28 | 28 | 0.0000 | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | language:hi | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | scan:not_scan | 24 | 28 | 28 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| unmess_parsing | overall:overall | 28 | 32 | 20 | 0.0000 | 1.0000 | 0.4286 | 0.0227 | 0.5714 |
| unmess_parsing | category:bilingual | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0214 | 0.0000 |
| unmess_parsing | category:clean | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0016 | 0.0000 |
| unmess_parsing | category:gst_invoice | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | 0.0195 | 1.0000 |
| unmess_parsing | category:merged_table | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | 0.0198 | 1.0000 |
| unmess_parsing | category:receipt | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0017 | 0.0000 |
| unmess_parsing | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 0.0000 | 0.0759 | 1.0000 |
| unmess_parsing | category:spanning_table | 4 | 8 | 8 | 0.0000 | n/a | 0.0000 | 0.0188 | 1.0000 |
| unmess_parsing | language:en | 24 | 28 | 20 | 0.0000 | 1.0000 | 0.3333 | 0.0229 | 0.6667 |
| unmess_parsing | language:hi | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0214 | 0.0000 |
| unmess_parsing | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | 0.0781 | 1.0000 |
| unmess_parsing | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | 0.0831 | 1.0000 |
| unmess_parsing | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 0.0000 | 0.0713 | 1.0000 |
| unmess_parsing | scan:not_scan | 24 | 28 | 16 | 0.0000 | n/a | 0.5000 | 0.0138 | 0.5000 |

## Dev results

| System | Group | Documents | Pages | Failed pages | table_f1 | ocr_cer | cheap_parser_share | latency_per_page_s | failed_page_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | overall:overall | 28 | 32 | 4 | 0.0000 | 1.0000 | 1.0000 | 0.0013 | 0.1429 |
| pymupdf_fixed | category:bilingual | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:clean | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0016 | 0.0000 |
| pymupdf_fixed | category:gst_invoice | 4 | 4 | 0 | 0.0000 | n/a | 1.0000 | 0.0017 | 0.0000 |
| pymupdf_fixed | category:merged_table | 4 | 4 | 0 | 0.0000 | n/a | 1.0000 | 0.0018 | 0.0000 |
| pymupdf_fixed | category:receipt | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | category:spanning_table | 4 | 8 | 0 | 0.0000 | n/a | 1.0000 | 0.0011 | 0.0000 |
| pymupdf_fixed | language:en | 24 | 28 | 4 | 0.0000 | 1.0000 | 1.0000 | 0.0013 | 0.1667 |
| pymupdf_fixed | language:hi | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 1.0000 | 0.0005 | 1.0000 |
| pymupdf_fixed | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 1.0000 | 0.0005 | 1.0000 |
| pymupdf_fixed | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:not_scan | 24 | 28 | 0 | 0.0000 | n/a | 1.0000 | 0.0014 | 0.0000 |
| docling_only | overall:overall | 28 | 32 | 32 | 0.0000 | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | category:bilingual | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:clean | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:gst_invoice | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:merged_table | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:receipt | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | category:spanning_table | 4 | 8 | 8 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | language:en | 24 | 28 | 28 | 0.0000 | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | language:hi | 4 | 4 | 4 | n/a | n/a | 0.0000 | n/a | 1.0000 |
| docling_only | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 0.0000 | n/a | 1.0000 |
| docling_only | scan:not_scan | 24 | 28 | 28 | 0.0000 | n/a | 0.0000 | n/a | 1.0000 |
| unmess_parsing | overall:overall | 28 | 32 | 20 | 0.0000 | 1.0000 | 0.4286 | 0.0232 | 0.5714 |
| unmess_parsing | category:bilingual | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0215 | 0.0000 |
| unmess_parsing | category:clean | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0017 | 0.0000 |
| unmess_parsing | category:gst_invoice | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | 0.0194 | 1.0000 |
| unmess_parsing | category:merged_table | 4 | 4 | 4 | 0.0000 | n/a | 0.0000 | 0.0199 | 1.0000 |
| unmess_parsing | category:receipt | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0017 | 0.0000 |
| unmess_parsing | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 0.0000 | 0.0794 | 1.0000 |
| unmess_parsing | category:spanning_table | 4 | 8 | 8 | 0.0000 | n/a | 0.0000 | 0.0189 | 1.0000 |
| unmess_parsing | language:en | 24 | 28 | 20 | 0.0000 | 1.0000 | 0.3333 | 0.0235 | 0.6667 |
| unmess_parsing | language:hi | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0215 | 0.0000 |
| unmess_parsing | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | 0.0771 | 1.0000 |
| unmess_parsing | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | 0.0982 | 1.0000 |
| unmess_parsing | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 0.0000 | 0.0711 | 1.0000 |
| unmess_parsing | scan:not_scan | 24 | 28 | 16 | 0.0000 | n/a | 0.5000 | 0.0138 | 0.5000 |

## Dev quality calibration

Spearman rho: 0.9752 over 32 pages.
This strong correlation is dominated by unavailable Docling/Ollama pages scoring zero; it does not establish calibration among successful parses.
Page accuracy: mean of clipped normalized-text similarity and page table F1 where tables exist.

| Score bucket | Pages | Mean page accuracy |
|---|---:|---:|
| 0.00-0.25 | 20 | 0.0000 |
| 0.25-0.50 | 0 | n/a |
| 0.50-0.75 | 0 | n/a |
| 0.75-1.00 | 12 | 0.9833 |

## Test comparison with PyMuPDF baseline

- bilingual: no measured loss
- clean: no measured loss
- gst_invoice: failed pages
- merged_table: failed pages
- receipt: no measured loss
- scan: no measured loss
- spanning_table: failed pages

VLM-dependent test pages that failed: 20. They remain in every metric denominator; see failure details below.

## Parser failures

- test / pymupdf_fixed / synthetic-scan-01 page 1: pymupdf: no embedded text
- test / pymupdf_fixed / synthetic-scan-03 page 1: pymupdf: no embedded text
- test / pymupdf_fixed / synthetic-scan-05 page 1: pymupdf: no embedded text
- test / pymupdf_fixed / synthetic-scan-07 page 1: pymupdf: no embedded text
- test / docling_only / synthetic-clean-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-clean-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-clean-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-clean-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-scan-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-scan-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-scan-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-scan-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-receipt-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-receipt-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-receipt-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-receipt-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-gst_invoice-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-gst_invoice-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-gst_invoice-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-gst_invoice-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-merged_table-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-merged_table-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-merged_table-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-merged_table-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-01 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-03 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-05 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-spanning_table-07 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-bilingual-01 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-bilingual-03 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-bilingual-05 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / docling_only / synthetic-bilingual-07 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- test / unmess_parsing / synthetic-scan-01 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-scan-03 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-scan-05 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-scan-07 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-gst_invoice-01 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-gst_invoice-03 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-gst_invoice-05 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-gst_invoice-07 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-merged_table-01 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-merged_table-03 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-merged_table-05 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-merged_table-07 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-01 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-01 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-03 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-03 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-05 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-05 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-07 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- test / unmess_parsing / synthetic-spanning_table-07 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / pymupdf_fixed / synthetic-scan-00 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-02 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-04 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-06 page 1: pymupdf: no embedded text
- dev / docling_only / synthetic-clean-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-clean-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-clean-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-clean-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-scan-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-scan-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-scan-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-scan-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-receipt-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-receipt-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-receipt-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-receipt-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-gst_invoice-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-gst_invoice-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-gst_invoice-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-gst_invoice-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-merged_table-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-merged_table-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-merged_table-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-merged_table-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-00 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-02 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-04 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-spanning_table-06 page 2: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-bilingual-00 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-bilingual-02 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-bilingual-04 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / docling_only / synthetic-bilingual-06 page 1: unavailable: RuntimeError: skipped: optional dependency not installed
- dev / unmess_parsing / synthetic-scan-00 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-scan-02 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-scan-04 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-scan-06 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-gst_invoice-00 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-gst_invoice-02 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-gst_invoice-04 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-gst_invoice-06 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-merged_table-00 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-merged_table-02 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-merged_table-04 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-merged_table-06 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-00 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-00 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-02 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-02 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-04 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-04 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-06 page 1: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)
- dev / unmess_parsing / synthetic-spanning_table-06 page 2: vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not permitted (attempts: docling: ParserUnavailable: Docling unavailable: install the [parsers] extra, vlm: ConnectError: [Errno 1] Operation not permitted; ConnectError: [Errno 1] Operation not per)

See EVAL.md for metric definitions and dataset limits.
