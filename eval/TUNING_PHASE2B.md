# Phase 2b dev-only tuning log

No Phase 2b test split has been run. The first Phase 2 test run under freeze commit
`caa7f35c2f46777eba1a690e0292dac1ea04fe39` was invalid because the intended
backends were unavailable; it is retained as a superseded audit record. No routing or
quality-gate threshold was changed after looking at that test run. All trials below
use only the 28-document, 32-page dev split and model tag `qwen2.5vl:latest`.

| Dev trial | Change from starting value | Measured effect | Decision |
|---|---|---|---|
| Starting operational state with cached Docling artifacts | VLM timeout 3 s; prompt `phase2-v1` | Unmess: 4 failed scan pages; scan CER 1.0000; table F1 0.5417; cheap-parser share 0.4286. The VLM timed out on every dev scan. | Revise VLM contract and timeout. |
| Vision runtime/contract | Timeout 3 → 120 s; prompt `phase2-v1` → `phase2b-v2` (strict Markdown-only JSON, whole-page bbox) | Unmess: 0 failed pages; scan CER 0.0287; table F1 0.5417; cheap share 0.4286. Four VLM pages took 54.6155 s total, including one cache hit; three uncached pages took 54.5798 s (0.0550 pages/s). | Keep for dev stage; precise VLM bboxes and table cells remain limitations. |
| Layout-threshold sensitivity | `parser_complex_layout_threshold` 0.90 → 0.80 for one dev-only trial | Cheap-parser share fell from 0.4286 to 0.0000; table F1 stayed 0.5417 and scan CER stayed 0.0287. | Reject; retain 0.90. |
| Review-gate sensitivity | `quality_review_threshold` 0.70 → 0.95 for one dev-only trial | Table F1 0.5417, scan CER 0.0287, cheap share 0.4286, failures 0, escalations 0: no measured change. | Reject; retain 0.70. |

The final dev routing/gate values remain those in `eval/config/phase2b_dev.toml`.
All 32 successful dev pages received quality score 1.0, so no in-range gate threshold
can distinguish them or trigger an escalation. Successful-only Spearman is undefined.
This is a calibration weakness, not a reason to tune against the test split.

Where Unmess does not win on dev: merged-table F1 is 0.0000, tied with Docling-only;
GST-invoice F1 ties Docling-only at 1.0000; overall latency (2.2093 s/page) is worse
than Docling-only (1.7775 s/page) and much slower than PyMuPDF (0.0014 s/page).
The dev report gives all category, language, and scan-difficulty breakdowns.
