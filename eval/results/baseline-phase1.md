# Unmess evaluation report

Run: 2026-10-09T21:06:38.901664+00:00 | Git: `44fb20b00b4dbf8fca42a072ddde0315ffeab63c` | dirty: True
Dataset: 56 PDFs, 1374226 bytes; generator 1.0.0, seed 20261010
Python 3.11.15; libraries: pymupdf 1.28.2, reportlab 4.5.1, pillow 12.3.0, pydantic 2.14.0
Platform: macOS-26.6.2-arm64-arm-64bit; font SHA-256: `14ec4af41f27482216d1c2229f417ff9b1425e1babb014e57d1d40d03229853e`
Models: none used. Retrieval: in-memory BM25.

Test is the headline split. Dev is for threshold tuning only.

## Test results

| System | Group | Documents | table_f1 | ocr_cer | recall_at_1 | recall_at_3 | mrr | table_split_rate | citation_accuracy | cheap_parser_share | latency_per_page_s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | overall:overall | 28 | 0.0000 | 1.0000 | 0.6857 | 0.7000 | 0.7002 | 1.0000 | 0.6857 | 1.0000 | 0.0012 |
| pymupdf_fixed | category:bilingual | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0010 |
| pymupdf_fixed | category:clean | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0011 |
| pymupdf_fixed | category:gst_invoice | 4 | 0.0000 | n/a | 0.6000 | 0.6000 | 0.6180 | 1.0000 | 0.6000 | 1.0000 | 0.0017 |
| pymupdf_fixed | category:merged_table | 4 | 0.0000 | n/a | 0.6000 | 0.6000 | 0.6149 | 1.0000 | 0.6000 | 1.0000 | 0.0018 |
| pymupdf_fixed | category:receipt | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0010 |
| pymupdf_fixed | category:scan | 4 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0006 |
| pymupdf_fixed | category:spanning_table | 4 | 0.0000 | n/a | 0.6000 | 0.7000 | 0.6684 | 1.0000 | 0.6000 | 1.0000 | 0.0011 |
| pymupdf_fixed | language:en | 24 | 0.0000 | 1.0000 | 0.6333 | 0.6500 | 0.6502 | 1.0000 | 0.6333 | 1.0000 | 0.0012 |
| pymupdf_fixed | language:hi | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0010 |
| pymupdf_fixed | scan:high | 1 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0005 |
| pymupdf_fixed | scan:low | 1 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0005 |
| pymupdf_fixed | scan:medium | 2 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0006 |
| pymupdf_fixed | scan:not_scan | 24 | 0.0000 | n/a | 0.8000 | 0.8167 | 0.8169 | 1.0000 | 0.8000 | 1.0000 | 0.0013 |
| docling_only (skipped: optional dependency not installed) | overall | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| unmess (not implemented yet) | overall | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Dev results

| System | Group | Documents | table_f1 | ocr_cer | recall_at_1 | recall_at_3 | mrr | table_split_rate | citation_accuracy | cheap_parser_share | latency_per_page_s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | overall:overall | 28 | 0.0000 | 1.0000 | 0.6857 | 0.7000 | 0.7018 | 1.0000 | 0.6857 | 1.0000 | 0.0013 |
| pymupdf_fixed | category:bilingual | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0010 |
| pymupdf_fixed | category:clean | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0019 |
| pymupdf_fixed | category:gst_invoice | 4 | 0.0000 | n/a | 0.6000 | 0.6000 | 0.6197 | 1.0000 | 0.6000 | 1.0000 | 0.0017 |
| pymupdf_fixed | category:merged_table | 4 | 0.0000 | n/a | 0.6000 | 0.6000 | 0.6159 | 1.0000 | 0.6000 | 1.0000 | 0.0018 |
| pymupdf_fixed | category:receipt | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0010 |
| pymupdf_fixed | category:scan | 4 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0006 |
| pymupdf_fixed | category:spanning_table | 4 | 0.0000 | n/a | 0.6000 | 0.7000 | 0.6767 | 1.0000 | 0.6000 | 1.0000 | 0.0011 |
| pymupdf_fixed | language:en | 24 | 0.0000 | 1.0000 | 0.6333 | 0.6500 | 0.6521 | 1.0000 | 0.6333 | 1.0000 | 0.0014 |
| pymupdf_fixed | language:hi | 4 | n/a | n/a | 1.0000 | 1.0000 | 1.0000 | n/a | 1.0000 | 1.0000 | 0.0010 |
| pymupdf_fixed | scan:high | 1 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0005 |
| pymupdf_fixed | scan:low | 1 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0005 |
| pymupdf_fixed | scan:medium | 2 | n/a | 1.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | 0.0000 | 1.0000 | 0.0006 |
| pymupdf_fixed | scan:not_scan | 24 | 0.0000 | n/a | 0.8000 | 0.8167 | 0.8187 | 1.0000 | 0.8000 | 1.0000 | 0.0014 |
| docling_only (skipped: optional dependency not installed) | overall | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| unmess (not implemented yet) | overall | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

Metric definitions and limitations: see EVAL.md.
