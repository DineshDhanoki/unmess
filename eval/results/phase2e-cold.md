# Phase 2e DEV cold-cache timing

Run: 2026-10-12T21:25:38.740160+00:00; order: `pymupdf_fixed -> docling_default -> docling_only -> unmess_parsing -> vlm_every_page`.
Vision model `qwen2.5vl`; Ollama `0.40.2`; prompt `phase2b-v2`.
Hardware: Mac16,12; Apple M4; memory 17179869184 bytes; OS macOS-26.6.2-arm64-arm-64bit.
Power check: `Now drawing from 'AC Power'
 -InternalBattery-0 (id=22544483)	100%; charged; 0:00 remaining present: true`.
Vision warm-up/load time, excluded from system timing: 6.3150 s.
Each VLM-using system had its own newly created empty response-cache directory and cache reads were disabled. A nonzero cache-hit count invalidates that system's cold timing. Retry time is included.

| System | Pages | Total COLD s | COLD s/page | Cache hits | Valid | Failures | CER | WER | Table F1 | Page accuracy |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| pymupdf_fixed | 52 | 0.7260 | 0.0140 | 0 | True | 8 | 0.9304 | 0.3362 | 0.0000 | 0.5048 |
| docling_default | 52 | 162.3456 | 3.1220 | 0 | True | 2 | 0.7377 | 0.4230 | 0.8214 | 0.6315 |
| docling_only | 52 | 281.3632 | 5.4108 | 0 | True | 2 | 0.5503 | 0.7212 | 0.8214 | 0.5223 |
| unmess_parsing | 52 | 643.8690 | 12.3821 | 0 | True | 0 | 0.0170 | 0.0331 | 0.8661 | 0.9815 |
| vlm_every_page | 52 | 1384.3580 | 26.6223 | 0 | True | 3 | 0.1731 | 0.2669 | 0.6472 | 0.8806 |

Only one pass was run because the pre-run estimate for two sequential passes exceeded 45 minutes. No result from one system populated another system's cache.
Each VLM cache started with zero files; post-run file counts are recorded in JSON.
Thermal limitation: not instrumented; retained as a timing limitation.

## Failures

- pymupdf_fixed / synthetic-scan-00 page 1: no embedded text
- pymupdf_fixed / synthetic-scan-02 page 1: no embedded text
- pymupdf_fixed / synthetic-scan-04 page 1: no embedded text
- pymupdf_fixed / synthetic-scan-06 page 1: no embedded text
- pymupdf_fixed / synthetic-mixed_pages-00 page 2: no embedded text
- pymupdf_fixed / synthetic-mixed_pages-02 page 2: no embedded text
- pymupdf_fixed / synthetic-mixed_pages-04 page 2: no embedded text
- pymupdf_fixed / synthetic-mixed_pages-06 page 2: no embedded text
- docling_default / synthetic-scan-06 page 1: no extracted text
- docling_default / synthetic-mixed_pages-06 page 2: no extracted text
- docling_only / synthetic-scan-04 page 1: no extracted text
- docling_only / synthetic-scan-06 page 1: no extracted text
- vlm_every_page / synthetic-merged_table-00 page 1: HTTPStatusError: Server error '500 Internal Server Error' for url 'http://localhost:11434/api/generate' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500; HTTPStatusError: Server error '500 Internal Se
- vlm_every_page / synthetic-merged_table-02 page 1: HTTPStatusError: Server error '500 Internal Server Error' for url 'http://localhost:11434/api/generate' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500; HTTPStatusError: Server error '500 Internal Se
- vlm_every_page / synthetic-merged_table-04 page 1: HTTPStatusError: Server error '500 Internal Server Error' for url 'http://localhost:11434/api/generate' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500; HTTPStatusError: Server error '500 Internal Se
