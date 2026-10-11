# Phase 2c DEV-only tuning and correction log

No Phase 2c test-split evaluation has run. The superseded Phase 2 freeze is not reused.
The routing and review thresholds in `eval/config/phase2b_dev.toml` have **not changed**.

| Change | DEV evidence before | DEV evidence after | Decision |
|---|---|---|---|
| Box the synthetic merged heading and align whole-table row origins in cell F1 | Original 28 DEV: merged-table F1 0.0000 for Docling and Unmess; overall table F1 0.5000 and 0.5417 | Same 28 DEV: merged-table F1 1.0000 for both; overall table F1 0.8333 and 0.8750 | Corrected layout/metric bug; not a routing threshold change. |
| Expand dataset with three hard categories and extra weak-category examples | Original cohort: 28 DEV documents, 32 pages | Expanded cohort: 15 DEV documents, 20 pages; combined: 43 documents, 52 pages | Report cohorts separately; never compare combined directly with Phase 2b. |
| Add all-page CER/WER and metric denominators | OCR-only CER left most categories without text accuracy | All-page CER/WER and per-cell document/page counts in Phase 2c report | Required metric coverage; no threshold tuned. |
| Replace saturated score mix with generic character/script plausibility and text–ink alignment | All 32 original DEV page scores landed in the top bucket | Expanded DEV calibration and escalation results recorded in the Phase 2c report | Signal change, not generator-specific corruption matching; thresholds unchanged. |

The first expanded DEV attempt could not reach localhost Ollama from the sandbox and recorded
12 VLM page failures. It is not used as a parser comparison. A permitted localhost run was
started next. It completed with 0 Unmess failures, 4 escalations, and 4 accuracy improvements;
8 of its 16 VLM attempts were uncached and took 212.598 seconds, while the whole Unmess parser
pass took 224.584 seconds. Its Spearman score/accuracy correlation was -0.0755 across 52
successful pages (0.50–0.75 bucket: 8 pages; 0.75–1.00: 44 pages), so calibration is weak
and slightly inverse. No gate threshold was changed: the existing 0.70 gate caught all four
DEV broken-text-layer pages and did not escalate clean digital pages. Test ground truth was
not read in either run.

The later full VLM-every-page pass was cache-warmed for many pages. Its 1,212.160 seconds for
52 pages and the routed pass's 24.971 seconds are **not** a controlled cold-cache speed
comparison. They are retained as measured operational costs, with cache state disclosed.
