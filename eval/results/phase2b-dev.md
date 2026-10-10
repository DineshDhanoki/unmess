# Unmess Phase 2b dev-only parsing evaluation

> **DEV ONLY — no replacement test run or new freeze.** This report uses the
> dev-tuning values in `eval/config/phase2b_dev.toml`. The freeze hash printed by the
> original runner below refers to the superseded Phase 2 run, not to a Phase 2b freeze.
> The measured VLM cost includes three uncached pages and one cache hit. VLM citations
> currently use a coarse full-page bbox, not a precise text-region bbox.

Run: 2026-10-10T18:25:41.533795+00:00 | Phase 2b working tree (uncommitted at measurement time) | no new freeze commit
Working tree dirty: True; dataset: 56 PDFs, 1374226 PDF bytes
Vision model: `qwen2.5vl`; prompt: `phase2b-v2`
Python 3.11.15; platform macOS-26.6.2-arm64-arm-64bit; libraries: pymupdf 1.28.2, reportlab 4.5.1, pillow 12.3.0, pydantic 2.14.0
Retrieval metrics: n/a until Phase 3. Dev is for tuning; test is evaluated only after freeze.

Dev-tuning values (not frozen): `{"parser_complex_layout_threshold": 0.9, "parser_garbled_ratio_threshold": 0.1, "parser_image_coverage_threshold": 0.7, "parser_max_skew_degrees": 3.0, "parser_scan_likelihood_threshold": 0.6, "parser_table_likelihood_threshold": 0.55, "parser_text_density_threshold": 0.12, "quality_review_threshold": 0.7, "vision_timeout_s": 120.0}`

## Dev results

| System | Group | Documents | Pages | Failed pages | table_f1 | ocr_cer | cheap_parser_share | latency_per_page_s | failed_page_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | overall:overall | 28 | 32 | 4 | 0.0000 | 1.0000 | 1.0000 | 0.0014 | 0.1429 |
| pymupdf_fixed | category:bilingual | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:clean | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0023 | 0.0000 |
| pymupdf_fixed | category:gst_invoice | 4 | 4 | 0 | 0.0000 | n/a | 1.0000 | 0.0018 | 0.0000 |
| pymupdf_fixed | category:merged_table | 4 | 4 | 0 | 0.0000 | n/a | 1.0000 | 0.0019 | 0.0000 |
| pymupdf_fixed | category:receipt | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | category:scan | 4 | 4 | 4 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | category:spanning_table | 4 | 8 | 0 | 0.0000 | n/a | 1.0000 | 0.0012 | 0.0000 |
| pymupdf_fixed | language:en | 24 | 28 | 4 | 0.0000 | 1.0000 | 1.0000 | 0.0014 | 0.1667 |
| pymupdf_fixed | language:hi | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0010 | 0.0000 |
| pymupdf_fixed | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:low | 1 | 1 | 1 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:medium | 2 | 2 | 2 | n/a | 1.0000 | 1.0000 | 0.0006 | 1.0000 |
| pymupdf_fixed | scan:not_scan | 24 | 28 | 0 | 0.0000 | n/a | 1.0000 | 0.0015 | 0.0000 |
| docling_only | overall:overall | 28 | 32 | 1 | 0.5000 | 0.2758 | 0.0000 | 1.7775 | 0.0357 |
| docling_only | category:bilingual | 4 | 4 | 0 | n/a | n/a | 0.0000 | 1.9228 | 0.0000 |
| docling_only | category:clean | 4 | 4 | 0 | n/a | n/a | 0.0000 | 2.5813 | 0.0000 |
| docling_only | category:gst_invoice | 4 | 4 | 0 | 1.0000 | n/a | 0.0000 | 1.2346 | 0.0000 |
| docling_only | category:merged_table | 4 | 4 | 0 | 0.0000 | n/a | 0.0000 | 1.6525 | 0.0000 |
| docling_only | category:receipt | 4 | 4 | 0 | n/a | n/a | 0.0000 | 1.9499 | 0.0000 |
| docling_only | category:scan | 4 | 4 | 1 | n/a | 0.2758 | 0.0000 | 2.2258 | 0.2500 |
| docling_only | category:spanning_table | 4 | 8 | 0 | 0.5000 | n/a | 0.0000 | 0.8753 | 0.0000 |
| docling_only | language:en | 24 | 28 | 1 | 0.5000 | 0.2758 | 0.0000 | 1.7532 | 0.0417 |
| docling_only | language:hi | 4 | 4 | 0 | n/a | n/a | 0.0000 | 1.9228 | 0.0000 |
| docling_only | scan:high | 1 | 1 | 1 | n/a | 1.0000 | 0.0000 | 3.3332 | 1.0000 |
| docling_only | scan:low | 1 | 1 | 0 | n/a | 0.0121 | 0.0000 | 1.5004 | 0.0000 |
| docling_only | scan:medium | 2 | 2 | 0 | n/a | 0.0455 | 0.0000 | 2.0348 | 0.0000 |
| docling_only | scan:not_scan | 24 | 28 | 0 | 0.5000 | n/a | 0.0000 | 1.7027 | 0.0000 |
| unmess_parsing | overall:overall | 28 | 32 | 0 | 0.5417 | 0.0287 | 0.4286 | 2.2093 | 0.0000 |
| unmess_parsing | category:bilingual | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0264 | 0.0000 |
| unmess_parsing | category:clean | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0067 | 0.0000 |
| unmess_parsing | category:gst_invoice | 4 | 4 | 0 | 1.0000 | n/a | 0.0000 | 0.9456 | 0.0000 |
| unmess_parsing | category:merged_table | 4 | 4 | 0 | 0.0000 | n/a | 0.0000 | 0.4456 | 0.0000 |
| unmess_parsing | category:receipt | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0035 | 0.0000 |
| unmess_parsing | category:scan | 4 | 4 | 0 | n/a | 0.0287 | 0.0000 | 13.7035 | 0.0000 |
| unmess_parsing | category:spanning_table | 4 | 8 | 0 | 0.6250 | n/a | 0.0000 | 0.3338 | 0.0000 |
| unmess_parsing | language:en | 24 | 28 | 0 | 0.5417 | 0.0287 | 0.3333 | 2.5731 | 0.0000 |
| unmess_parsing | language:hi | 4 | 4 | 0 | n/a | n/a | 1.0000 | 0.0264 | 0.0000 |
| unmess_parsing | scan:high | 1 | 1 | 0 | n/a | 0.0843 | 0.0000 | 18.5208 | 0.0000 |
| unmess_parsing | scan:low | 1 | 1 | 0 | n/a | 0.0000 | 0.0000 | 0.0932 | 0.0000 |
| unmess_parsing | scan:medium | 2 | 2 | 0 | n/a | 0.0152 | 0.0000 | 18.1000 | 0.0000 |
| unmess_parsing | scan:not_scan | 24 | 28 | 0 | 0.5417 | n/a | 0.5000 | 0.2936 | 0.0000 |

## Dev quality calibration

Spearman rho: n/a over 32 successfully parsed pages; 0 failed pages excluded.
All successful pages scored 1.0, so rank correlation is undefined and the scorer does
not discriminate among successful parses on this dev corpus.
Page accuracy: mean of clipped normalized-text similarity and page table F1 where tables exist.

| Score bucket | Pages | Mean page accuracy |
|---|---:|---:|
| 0.00-0.25 | 0 | n/a |
| 0.25-0.50 | 0 | n/a |
| 0.50-0.75 | 0 | n/a |
| 0.75-1.00 | 32 | 0.8817 |

## Dev VLM cost and escalation

VLM attempts: 4 pages in 54.6155 s (0.0732 pages/s).
Uncached VLM: 3 pages in 54.5798 s (0.0550 pages/s).
Escalated: 0 pages; accuracy improved on 0; mean accuracy delta n/a.

## Dev comparison and limitations

Unmess has zero dev page failures, versus one for Docling-only and four for PyMuPDF.
Its scan CER is 0.0287 versus Docling-only 0.2758, but scan latency is 13.7035 s/page
versus 2.2258 s/page. Overall latency is also worse than Docling-only (2.2093 versus
1.7775 s/page) and PyMuPDF (0.0014 s/page). GST-invoice table F1 ties Docling-only
at 1.0000; spanning-table F1 is 0.6250 versus 0.5000. Merged-table F1 remains
0.0000 for both. Clean, receipt, and bilingual categories have no table/OCR accuracy
metric in this parsing-stage report, so no accuracy win is claimed for them.

## Parser failures

- dev / pymupdf_fixed / synthetic-scan-00 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-02 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-04 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-06 page 1: pymupdf: no embedded text
- dev / docling_only / synthetic-scan-06 page 1: docling: no extracted text

See EVAL.md for metric definitions and dataset limits.
