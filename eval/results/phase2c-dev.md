# Unmess Phase 2c DEV-only parsing evaluation

Run: 2026-10-10T19:17:32.380151+00:00 | source commit `4f2b3846820987354cda501d9075a2c10ced0730` | freeze commit `not yet committed`
Working tree dirty: True; dataset: 43 PDFs, 2718246 PDF bytes
Vision model: `qwen2.5vl`; prompt: `phase2b-v2`
Python 3.11.15; platform macOS-26.6.2-arm64-arm-64bit; libraries: pymupdf 1.28.2, reportlab 4.5.1, pillow 12.3.0, pydantic 2.14.0, docling 2.137.0, torch 2.14.1
Retrieval metrics: n/a until Phase 3. Dev is for tuning; test is evaluated only after freeze.

Threshold source: `/Users/dineshdhanoki/unmess/eval/config/phase2b_dev.toml`
Threshold values: `{"parser_complex_layout_threshold": 0.9, "parser_garbled_ratio_threshold": 0.1, "parser_image_coverage_threshold": 0.7, "parser_max_skew_degrees": 3.0, "parser_scan_likelihood_threshold": 0.6, "parser_table_likelihood_threshold": 0.55, "parser_text_density_threshold": 0.12, "quality_review_threshold": 0.7, "vision_timeout_s": 120.0}`

## Dev results

| System | Group | Documents | Pages | Failed pages | table_f1 | ocr_cer | text_cer | text_wer | cheap_parser_share | latency_per_page_s | failed_page_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | overall:overall | 43 | 52 | 8 | 0.0000 (d=14,p=19) | 1.5562 (d=12,p=12) | 0.9304 (d=43,p=52) | 0.3362 (d=43,p=52) | 1.0000 (d=43,p=52) | 0.0015 (d=43,p=52) | 0.1395 (d=43,p=52) |
| pymupdf_fixed | cohort:expanded | 15 | 20 | 4 | 0.0000 (d=2,p=3) | 1.8344 (d=8,p=8) | 1.6802 (d=15,p=20) | 0.6727 (d=15,p=20) | 1.0000 (d=15,p=20) | 0.0014 (d=15,p=20) | 0.1333 (d=15,p=20) |
| pymupdf_fixed | cohort:original | 28 | 32 | 4 | 0.0000 (d=12,p=16) | 1.0000 (d=4,p=4) | 0.5287 (d=28,p=32) | 0.1558 (d=28,p=32) | 1.0000 (d=28,p=32) | 0.0016 (d=28,p=32) | 0.1429 (d=28,p=32) |
| pymupdf_fixed | category:bilingual | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0780 (d=5,p=5) | 0.0909 (d=5,p=5) | 1.0000 (d=5,p=5) | 0.0010 (d=5,p=5) | 0.0000 (d=5,p=5) |
| pymupdf_fixed | category:broken_text_layer | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 2.6526 (d=4,p=4) | 1.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0015 (d=4,p=4) | 0.0000 (d=4,p=4) |
| pymupdf_fixed | category:clean | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0301 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0034 (d=4,p=4) | 0.0000 (d=4,p=4) |
| pymupdf_fixed | category:fake_text_layer_scan | 4 | 4 | 0 | n/a (d=0,p=0) | 2.6687 (d=4,p=4) | 2.6687 (d=4,p=4) | 1.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0019 (d=4,p=4) | 0.0000 (d=4,p=4) |
| pymupdf_fixed | category:gst_invoice | 4 | 4 | 0 | 0.0000 (d=4,p=4) | n/a (d=0,p=0) | 0.7814 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0018 (d=4,p=4) | 0.0000 (d=4,p=4) |
| pymupdf_fixed | category:merged_table | 5 | 5 | 0 | 0.0000 (d=5,p=5) | n/a (d=0,p=0) | 0.7213 (d=5,p=5) | 0.0000 (d=5,p=5) | 1.0000 (d=5,p=5) | 0.0019 (d=5,p=5) | 0.0000 (d=5,p=5) |
| pymupdf_fixed | category:mixed_pages | 4 | 8 | 4 | n/a (d=0,p=0) | 1.0000 (d=4,p=4) | 0.5150 (d=4,p=8) | 0.5000 (d=4,p=8) | 1.0000 (d=4,p=8) | 0.0008 (d=4,p=8) | 0.5000 (d=4,p=8) |
| pymupdf_fixed | category:receipt | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0297 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0011 (d=4,p=4) | 0.0000 (d=4,p=4) |
| pymupdf_fixed | category:scan | 4 | 4 | 4 | n/a (d=0,p=0) | 1.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0006 (d=4,p=4) | 1.0000 (d=4,p=4) |
| pymupdf_fixed | category:spanning_table | 5 | 10 | 0 | 0.0000 (d=5,p=10) | n/a (d=0,p=0) | 1.0599 (d=5,p=10) | 0.0000 (d=5,p=10) | 1.0000 (d=5,p=10) | 0.0012 (d=5,p=10) | 0.0000 (d=5,p=10) |
| pymupdf_fixed | language:en | 38 | 47 | 8 | 0.0000 (d=14,p=19) | 1.5562 (d=12,p=12) | 1.0425 (d=38,p=47) | 0.3684 (d=38,p=47) | 1.0000 (d=38,p=47) | 0.0016 (d=38,p=47) | 0.1579 (d=38,p=47) |
| pymupdf_fixed | language:hi | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0780 (d=5,p=5) | 0.0909 (d=5,p=5) | 1.0000 (d=5,p=5) | 0.0010 (d=5,p=5) | 0.0000 (d=5,p=5) |
| pymupdf_fixed | scan:high | 3 | 4 | 2 | n/a (d=0,p=0) | 1.5522 (d=3,p=3) | 1.3905 (d=3,p=4) | 0.8333 (d=3,p=4) | 1.0000 (d=3,p=4) | 0.0012 (d=3,p=4) | 0.5000 (d=3,p=4) |
| pymupdf_fixed | scan:low | 3 | 4 | 2 | n/a (d=0,p=0) | 1.5576 (d=3,p=3) | 1.3959 (d=3,p=4) | 0.8333 (d=3,p=4) | 1.0000 (d=3,p=4) | 0.0010 (d=3,p=4) | 0.5000 (d=3,p=4) |
| pymupdf_fixed | scan:medium | 6 | 8 | 4 | n/a (d=0,p=0) | 1.5576 (d=6,p=6) | 1.3959 (d=6,p=8) | 0.8333 (d=6,p=8) | 1.0000 (d=6,p=8) | 0.0011 (d=6,p=8) | 0.5000 (d=6,p=8) |
| pymupdf_fixed | scan:not_scan | 31 | 36 | 0 | 0.0000 (d=14,p=19) | n/a (d=0,p=0) | 0.7507 (d=31,p=36) | 0.1437 (d=31,p=36) | 1.0000 (d=31,p=36) | 0.0017 (d=31,p=36) | 0.0000 (d=31,p=36) |
| docling_only | overall:overall | 43 | 52 | 1 | 0.8214 (d=14,p=19) | 1.0775 (d=12,p=12) | 0.6817 (d=43,p=52) | 0.3509 (d=43,p=52) | 0.0000 (d=43,p=52) | 2.3174 (d=43,p=52) | 0.0233 (d=43,p=52) |
| docling_only | cohort:expanded | 15 | 20 | 0 | 0.7500 (d=2,p=3) | 1.4783 (d=8,p=8) | 1.5415 (d=15,p=20) | 0.4467 (d=15,p=20) | 0.0000 (d=15,p=20) | 2.5715 (d=15,p=20) | 0.0000 (d=15,p=20) |
| docling_only | cohort:original | 28 | 32 | 1 | 0.8333 (d=12,p=16) | 0.2758 (d=4,p=4) | 0.2211 (d=28,p=32) | 0.2996 (d=28,p=32) | 0.0000 (d=28,p=32) | 2.1813 (d=28,p=32) | 0.0357 (d=28,p=32) |
| docling_only | category:bilingual | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0725 (d=5,p=5) | 0.0909 (d=5,p=5) | 0.0000 (d=5,p=5) | 2.7784 (d=5,p=5) | 0.0000 (d=5,p=5) |
| docling_only | category:broken_text_layer | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 2.6887 (d=4,p=4) | 0.4500 (d=4,p=4) | 0.0000 (d=4,p=4) | 2.3896 (d=4,p=4) | 0.0000 (d=4,p=4) |
| docling_only | category:clean | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0361 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 2.0526 (d=4,p=4) | 0.0000 (d=4,p=4) |
| docling_only | category:fake_text_layer_scan | 4 | 4 | 0 | n/a (d=0,p=0) | 2.7502 (d=4,p=4) | 2.7502 (d=4,p=4) | 0.7250 (d=4,p=4) | 0.0000 (d=4,p=4) | 3.1679 (d=4,p=4) | 0.0000 (d=4,p=4) |
| docling_only | category:gst_invoice | 4 | 4 | 0 | 1.0000 (d=4,p=4) | n/a (d=0,p=0) | 0.3149 (d=4,p=4) | 0.4600 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.3170 (d=4,p=4) | 0.0000 (d=4,p=4) |
| docling_only | category:merged_table | 5 | 5 | 0 | 1.0000 (d=5,p=5) | n/a (d=0,p=0) | 0.3805 (d=5,p=5) | 0.5000 (d=5,p=5) | 0.0000 (d=5,p=5) | 3.2372 (d=5,p=5) | 0.0000 (d=5,p=5) |
| docling_only | category:mixed_pages | 4 | 8 | 0 | n/a (d=0,p=0) | 0.2065 (d=4,p=4) | 0.1213 (d=4,p=8) | 0.2000 (d=4,p=8) | 0.0000 (d=4,p=8) | 2.4667 (d=4,p=8) | 0.0000 (d=4,p=8) |
| docling_only | category:receipt | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0357 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 2.1107 (d=4,p=4) | 0.0000 (d=4,p=4) |
| docling_only | category:scan | 4 | 4 | 1 | n/a (d=0,p=0) | 0.2758 (d=4,p=4) | 0.2758 (d=4,p=4) | 0.4375 (d=4,p=4) | 0.0000 (d=4,p=4) | 2.5258 (d=4,p=4) | 0.2500 (d=4,p=4) |
| docling_only | category:spanning_table | 5 | 10 | 0 | 0.5000 (d=5,p=10) | n/a (d=0,p=0) | 0.4318 (d=5,p=10) | 0.6091 (d=5,p=10) | 0.0000 (d=5,p=10) | 1.0895 (d=5,p=10) | 0.0000 (d=5,p=10) |
| docling_only | language:en | 38 | 47 | 1 | 0.8214 (d=14,p=19) | 1.0775 (d=12,p=12) | 0.7619 (d=38,p=47) | 0.3851 (d=38,p=47) | 0.0000 (d=38,p=47) | 2.2567 (d=38,p=47) | 0.0263 (d=38,p=47) |
| docling_only | language:hi | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0725 (d=5,p=5) | 0.0909 (d=5,p=5) | 0.0000 (d=5,p=5) | 2.7784 (d=5,p=5) | 0.0000 (d=5,p=5) |
| docling_only | scan:high | 3 | 4 | 1 | n/a (d=0,p=0) | 1.5422 (d=3,p=3) | 1.4257 (d=3,p=4) | 0.8333 (d=3,p=4) | 0.0000 (d=3,p=4) | 3.4359 (d=3,p=4) | 0.3333 (d=3,p=4) |
| docling_only | scan:low | 3 | 4 | 0 | n/a (d=0,p=0) | 0.9111 (d=3,p=3) | 0.9131 (d=3,p=4) | 0.3167 (d=3,p=4) | 0.0000 (d=3,p=4) | 1.7365 (d=3,p=4) | 0.0000 (d=3,p=4) |
| docling_only | scan:medium | 6 | 8 | 0 | n/a (d=0,p=0) | 0.9283 (d=6,p=6) | 0.9288 (d=6,p=8) | 0.3333 (d=6,p=8) | 0.0000 (d=6,p=8) | 2.8541 (d=6,p=8) | 0.0000 (d=6,p=8) |
| docling_only | scan:not_scan | 31 | 36 | 0 | 0.8214 (d=14,p=19) | n/a (d=0,p=0) | 0.5395 (d=31,p=36) | 0.3110 (d=31,p=36) | 0.0000 (d=31,p=36) | 2.1615 (d=31,p=36) | 0.0000 (d=31,p=36) |
| unmess_parsing | overall:overall | 43 | 52 | 0 | 0.8661 (d=14,p=19) | 0.0306 (d=12,p=12) | 0.0190 (d=43,p=52) | 0.0437 (d=43,p=52) | 0.3488 (d=43,p=52) | 0.5055 (d=43,p=52) | 0.0000 (d=43,p=52) |
| unmess_parsing | cohort:expanded | 15 | 20 | 0 | 0.8125 (d=2,p=3) | 0.0316 (d=8,p=8) | 0.0255 (d=15,p=20) | 0.0711 (d=15,p=20) | 0.2000 (d=15,p=20) | 0.2628 (d=15,p=20) | 0.0000 (d=15,p=20) |
| unmess_parsing | cohort:original | 28 | 32 | 0 | 0.8750 (d=12,p=16) | 0.0287 (d=4,p=4) | 0.0155 (d=28,p=32) | 0.0291 (d=28,p=32) | 0.4286 (d=28,p=32) | 0.6355 (d=28,p=32) | 0.0000 (d=28,p=32) |
| unmess_parsing | category:bilingual | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0502 (d=5,p=5) | 0.0909 (d=5,p=5) | 1.0000 (d=5,p=5) | 0.0425 (d=5,p=5) | 0.0000 (d=5,p=5) |
| unmess_parsing | category:broken_text_layer | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0301 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0814 (d=4,p=4) | 0.0000 (d=4,p=4) |
| unmess_parsing | category:clean | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0166 (d=4,p=4) | 0.0000 (d=4,p=4) |
| unmess_parsing | category:fake_text_layer_scan | 4 | 4 | 0 | n/a (d=0,p=0) | 0.0316 (d=4,p=4) | 0.0316 (d=4,p=4) | 0.1625 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.1368 (d=4,p=4) | 0.0000 (d=4,p=4) |
| unmess_parsing | category:gst_invoice | 4 | 4 | 0 | 1.0000 (d=4,p=4) | n/a (d=0,p=0) | 0.0045 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.0090 (d=4,p=4) | 0.0000 (d=4,p=4) |
| unmess_parsing | category:merged_table | 5 | 5 | 0 | 1.0000 (d=5,p=5) | n/a (d=0,p=0) | 0.0150 (d=5,p=5) | 0.0000 (d=5,p=5) | 0.0000 (d=5,p=5) | 2.5935 (d=5,p=5) | 0.0000 (d=5,p=5) |
| unmess_parsing | category:mixed_pages | 4 | 8 | 0 | n/a (d=0,p=0) | 0.0316 (d=4,p=4) | 0.0158 (d=4,p=8) | 0.0813 (d=4,p=8) | 0.5000 (d=4,p=8) | 0.0581 (d=4,p=8) | 0.0000 (d=4,p=8) |
| unmess_parsing | category:receipt | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 1.0000 (d=4,p=4) | 0.0026 (d=4,p=4) | 0.0000 (d=4,p=4) |
| unmess_parsing | category:scan | 4 | 4 | 0 | n/a (d=0,p=0) | 0.0287 (d=4,p=4) | 0.0287 (d=4,p=4) | 0.1125 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0837 (d=4,p=4) | 0.0000 (d=4,p=4) |
| unmess_parsing | category:spanning_table | 5 | 10 | 0 | 0.6250 (d=5,p=10) | n/a (d=0,p=0) | 0.0094 (d=5,p=10) | 0.0000 (d=5,p=10) | 0.0000 (d=5,p=10) | 0.6007 (d=5,p=10) | 0.0000 (d=5,p=10) |
| unmess_parsing | language:en | 38 | 47 | 0 | 0.8661 (d=14,p=19) | 0.0306 (d=12,p=12) | 0.0149 (d=38,p=47) | 0.0375 (d=38,p=47) | 0.2632 (d=38,p=47) | 0.5664 (d=38,p=47) | 0.0000 (d=38,p=47) |
| unmess_parsing | language:hi | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0502 (d=5,p=5) | 0.0909 (d=5,p=5) | 1.0000 (d=5,p=5) | 0.0425 (d=5,p=5) | 0.0000 (d=5,p=5) |
| unmess_parsing | scan:high | 3 | 4 | 0 | n/a (d=0,p=0) | 0.1124 (d=3,p=3) | 0.0914 (d=3,p=4) | 0.4750 (d=3,p=4) | 0.1667 (d=3,p=4) | 0.0936 (d=3,p=4) | 0.0000 (d=3,p=4) |
| unmess_parsing | scan:low | 3 | 4 | 0 | n/a (d=0,p=0) | 0.0000 (d=3,p=3) | 0.0000 (d=3,p=4) | 0.0000 (d=3,p=4) | 0.1667 (d=3,p=4) | 0.0894 (d=3,p=4) | 0.0000 (d=3,p=4) |
| unmess_parsing | scan:medium | 6 | 8 | 0 | n/a (d=0,p=0) | 0.0051 (d=6,p=6) | 0.0051 (d=6,p=8) | 0.0000 (d=6,p=8) | 0.1667 (d=6,p=8) | 0.0942 (d=6,p=8) | 0.0000 (d=6,p=8) |
| unmess_parsing | scan:not_scan | 31 | 36 | 0 | 0.8661 (d=14,p=19) | n/a (d=0,p=0) | 0.0165 (d=31,p=36) | 0.0147 (d=31,p=36) | 0.4194 (d=31,p=36) | 0.6652 (d=31,p=36) | 0.0000 (d=31,p=36) |
| vlm_every_page | overall:overall | 43 | 52 | 3 | 0.0000 (d=14,p=19) | 0.0306 (d=12,p=12) | 0.1731 (d=43,p=52) | 0.2669 (d=43,p=52) | 0.0000 (d=43,p=52) | 24.0631 (d=43,p=52) | 0.0698 (d=43,p=52) |
| vlm_every_page | cohort:expanded | 15 | 20 | 0 | 0.0000 (d=2,p=3) | 0.0316 (d=8,p=8) | 0.0701 (d=15,p=20) | 0.1502 (d=15,p=20) | 0.0000 (d=15,p=20) | 7.5193 (d=15,p=20) | 0.0000 (d=15,p=20) |
| vlm_every_page | cohort:original | 28 | 32 | 3 | 0.0000 (d=12,p=16) | 0.0287 (d=4,p=4) | 0.2283 (d=28,p=32) | 0.3294 (d=28,p=32) | 0.0000 (d=28,p=32) | 32.9258 (d=28,p=32) | 0.1071 (d=28,p=32) |
| vlm_every_page | category:bilingual | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0334 (d=5,p=5) | 0.0000 (d=5,p=5) | 0.0000 (d=5,p=5) | 34.8263 (d=5,p=5) | 0.0000 (d=5,p=5) |
| vlm_every_page | category:broken_text_layer | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0301 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0181 (d=4,p=4) | 0.0000 (d=4,p=4) |
| vlm_every_page | category:clean | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0301 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 32.8267 (d=4,p=4) | 0.0000 (d=4,p=4) |
| vlm_every_page | category:fake_text_layer_scan | 4 | 4 | 0 | n/a (d=0,p=0) | 0.0316 (d=4,p=4) | 0.0316 (d=4,p=4) | 0.1625 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0669 (d=4,p=4) | 0.0000 (d=4,p=4) |
| vlm_every_page | category:gst_invoice | 4 | 4 | 0 | 0.0000 (d=4,p=4) | n/a (d=0,p=0) | 0.2783 (d=4,p=4) | 0.5400 (d=4,p=4) | 0.0000 (d=4,p=4) | 40.3720 (d=4,p=4) | 0.0000 (d=4,p=4) |
| vlm_every_page | category:merged_table | 5 | 5 | 3 | 0.0000 (d=5,p=5) | n/a (d=0,p=0) | 0.7029 (d=5,p=5) | 0.8000 (d=5,p=5) | 0.0000 (d=5,p=5) | 53.2155 (d=5,p=5) | 0.6000 (d=5,p=5) |
| vlm_every_page | category:mixed_pages | 4 | 8 | 0 | n/a (d=0,p=0) | 0.0316 (d=4,p=4) | 0.0309 (d=4,p=8) | 0.0813 (d=4,p=8) | 0.0000 (d=4,p=8) | 0.0397 (d=4,p=8) | 0.0000 (d=4,p=8) |
| vlm_every_page | category:receipt | 4 | 4 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0223 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0000 (d=4,p=4) | 30.9363 (d=4,p=4) | 0.0000 (d=4,p=4) |
| vlm_every_page | category:scan | 4 | 4 | 0 | n/a (d=0,p=0) | 0.0287 (d=4,p=4) | 0.0287 (d=4,p=4) | 0.1125 (d=4,p=4) | 0.0000 (d=4,p=4) | 0.0446 (d=4,p=4) | 0.0000 (d=4,p=4) |
| vlm_every_page | category:spanning_table | 5 | 10 | 0 | 0.0000 (d=5,p=10) | n/a (d=0,p=0) | 0.3908 (d=5,p=10) | 0.7783 (d=5,p=10) | 0.0000 (d=5,p=10) | 35.4576 (d=5,p=10) | 0.0000 (d=5,p=10) |
| vlm_every_page | language:en | 38 | 47 | 3 | 0.0000 (d=14,p=19) | 0.0306 (d=12,p=12) | 0.1915 (d=38,p=47) | 0.3020 (d=38,p=47) | 0.0000 (d=38,p=47) | 22.6469 (d=38,p=47) | 0.0789 (d=38,p=47) |
| vlm_every_page | language:hi | 5 | 5 | 0 | n/a (d=0,p=0) | n/a (d=0,p=0) | 0.0334 (d=5,p=5) | 0.0000 (d=5,p=5) | 0.0000 (d=5,p=5) | 34.8263 (d=5,p=5) | 0.0000 (d=5,p=5) |
| vlm_every_page | scan:high | 3 | 4 | 0 | n/a (d=0,p=0) | 0.1124 (d=3,p=3) | 0.0964 (d=3,p=4) | 0.4750 (d=3,p=4) | 0.0000 (d=3,p=4) | 0.0570 (d=3,p=4) | 0.0000 (d=3,p=4) |
| vlm_every_page | scan:low | 3 | 4 | 0 | n/a (d=0,p=0) | 0.0000 (d=3,p=3) | 0.0050 (d=3,p=4) | 0.0000 (d=3,p=4) | 0.0000 (d=3,p=4) | 0.0423 (d=3,p=4) | 0.0000 (d=3,p=4) |
| vlm_every_page | scan:medium | 6 | 8 | 0 | n/a (d=0,p=0) | 0.0051 (d=6,p=6) | 0.0101 (d=6,p=8) | 0.0000 (d=6,p=8) | 0.0000 (d=6,p=8) | 0.0511 (d=6,p=8) | 0.0000 (d=6,p=8) |
| vlm_every_page | scan:not_scan | 31 | 36 | 3 | 0.0000 (d=14,p=19) | n/a (d=0,p=0) | 0.2284 (d=31,p=36) | 0.3242 (d=31,p=36) | 0.0000 (d=31,p=36) | 33.3584 (d=31,p=36) | 0.0968 (d=31,p=36) |

## Dev quality calibration

Spearman rho: -0.0755 over 52 successfully parsed pages; 0 failed pages excluded.
Page accuracy: mean of clipped normalized-text similarity and page table F1 where tables exist.

| Score bucket | Pages | Mean page accuracy |
|---|---:|---:|
| 0.00-0.25 | 0 | n/a |
| 0.25-0.50 | 0 | n/a |
| 0.50-0.75 | 8 | 0.9842 |
| 0.75-1.00 | 44 | 0.9753 |

## Dev VLM cost and escalation

VLM attempts: 16 pages in 0.9489 s (16.8618 pages/s).
Uncached VLM: 0 pages in 0 s (n/a pages/s).
Escalated: 4 pages; accuracy improved on 4; mean accuracy delta 1.0000.

## Accuracy versus cost

| System | DEV documents | DEV pages | Mean page accuracy | Text CER | Table F1 | Total parser time (s) | s/page |
|---|---:|---:|---:|---:|---:|---:|---:|
| pymupdf_fixed | 43 | 52 | 0.5048 | 0.9304 | 0.0000 | 0.0734 | 0.0014 |
| docling_only | 43 | 52 | 0.5529 | 0.6817 | 0.8214 | 114.9610 | 2.2108 |
| unmess_parsing | 43 | 52 | 0.9767 | 0.0190 | 0.8661 | 24.9713 | 0.4802 |
| vlm_every_page | 43 | 52 | 0.7394 | 0.1731 | 0.0000 | 1212.1601 | 23.3108 |

## Where Unmess loses on DEV

Lower CER is better; higher table F1 and page accuracy are better. Latency and accuracy must be judged together; cache-warmed VLM time is not a cold-run cost estimate.

- bilingual vs docling_only: mean_page_accuracy.
- bilingual vs vlm_every_page: text_cer, text_wer, mean_page_accuracy.

## Parser failures

- dev / pymupdf_fixed / synthetic-scan-00 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-02 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-04 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-scan-06 page 1: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-mixed_pages-00 page 2: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-mixed_pages-02 page 2: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-mixed_pages-04 page 2: pymupdf: no embedded text
- dev / pymupdf_fixed / synthetic-mixed_pages-06 page 2: pymupdf: no embedded text
- dev / docling_only / synthetic-scan-06 page 1: docling: no extracted text
- dev / vlm_every_page / synthetic-merged_table-00 page 1: vlm: HTTPStatusError: Server error '500 Internal Server Error' for url 'http://localhost:11434/api/generate' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTT
- dev / vlm_every_page / synthetic-merged_table-02 page 1: vlm: HTTPStatusError: Server error '500 Internal Server Error' for url 'http://localhost:11434/api/generate' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTT
- dev / vlm_every_page / synthetic-merged_table-04 page 1: vlm: HTTPStatusError: Server error '500 Internal Server Error' for url 'http://localhost:11434/api/generate' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTT

Metric cells show their own document and page denominators. Means are document-weighted; time is measured end-to-end in each adapter. The VLM cache was warm for the routed Unmess pass and partly cold for the VLM-every-page pass. These timings are not an apples-to-apples cold-cost comparison; no general speed advantage is claimed.
See EVAL.md for metric definitions and dataset limits.
