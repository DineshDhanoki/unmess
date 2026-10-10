# Evaluation contract

## Corpus and splits

`scripts/make_synthetic_docs.py` generates 56 wholly fictional PDFs: eight each of clean
digital pages, degraded scans, receipts, GST-style invoices, merged-cell tables, tables spanning
two pages, and bilingual English/Hindi pages. Every category has four `dev` and four `test`
documents. The fixed seed is `20261010`. The generator records PDF SHA-256 hashes, version,
seed, fixed metadata, and font hash in `eval/datasets/MANIFEST.json`. The committed PDFs total
1,374,226 bytes in generator version 1.0.0. The font is downloaded separately under the SIL
Open Font License and is not committed.

Use `dev` to tune routing thresholds, chunk sizes, or other choices. **Never tune on `test`.**
The report presents test first and labels it as the headline split. Dev and test are evaluated
in separate retrieval pools, so documents from one split cannot be retrieved by the other.

Ground truth for each document contains one-based pages with `expected_text`, `language`, and
`is_ocr_page`; tables with `page_numbers`, cells, spans, and normalized page bounding boxes;
3–5 questions with `answer_type`, `answer_aliases`, `language`, answering pages and boxes; and
scan parameters (`rotation_deg`, `noise_level`, `dpi`, `blur`) where applicable. The `split` field
is `dev` or `test`. GSTINs and identities are visibly invalid and fictional.

For tables spanning pages, the visible header repeats on page two. Header cells repeat at row
index zero; data row indices continue from page one. `has_merged_cells` and `spans_pages` flags
must agree with the underlying cells and page count. Box coordinates are normalized to 0–1,
with the origin at the top left. A box must have positive area.

## Systems

- `pymupdf_fixed`: plain PyMuPDF text extraction and fixed 16-word windows with 3-word
  overlap. It does not perform OCR or structured table extraction.
- `docling_only`: optional Docling extraction. If `[parsers]` is not installed, the report says
  `skipped: optional dependency not installed`. When installed, model downloads are disabled
  during evaluation; required local artifacts must already be present.
- `unmess`: a registered `PipelineAdapter` placeholder. Phase 1 reports `not implemented yet`
  and `n/a` values. The full pipeline belongs to later phases.

Phase 2 replaces the placeholder in new runs with `unmess_parsing`: routing, page parsing, and
quality scoring only. The committed Phase 1 baseline report remains unchanged. The new parsing
report compares PyMuPDF, Docling, and Unmess on table F1, OCR CER, cheap-parser share, latency,
and failed-page rate. Retrieval metrics are `n/a` for all Phase 2 systems until Phase 3.
Unavailable Docling and unreachable Ollama are counted as failed pages and listed by document
and page, including attempted parser errors.

Retrieval uses an in-memory BM25 index for every available parser, with the same question set
and split-specific corpus. It does not use Qdrant or Ollama in Phase 1.

## Metric definitions

The runner reports document-macro averages overall and by category, language, and scan
difficulty. `n/a` means the measure has no applicable reference or the system did not run.

- **Table cell F1:** exact multiset matching of table ID, row, column, row span, column span,
  and stripped cell text. Precision and recall determine F1. Only documents with reference
  tables enter this average.
- **OCR CER:** Levenshtein character edits divided by reference characters on pages marked
  `is_ocr_page`. No extracted text therefore scores 1.0 on nonempty reference text.
- **Recall@1/3 and MRR:** each question is a query. A retrieved chunk is relevant only when
  its document ID matches, it overlaps an answering page, and, if answer boxes exist, one of
  its boxes intersects an answer box. Recall@k is a binary hit per question. MRR is reciprocal
  rank of the first relevant chunk. Scores are averaged within each document, then across
  documents. Alias strings are preserved for later answer checking but do not change geometric
  retrieval relevance.
- **Table split rate:** fraction of reference tables whose nonempty cell text does not all
  appear in any single chunk. This is 1.0 if every table is split; lower is better.
- **Citation accuracy:** fraction of questions whose top-ranked chunk cites the correct
  document, answering page, and intersecting answer box when one exists.
- **Cheap parser share:** fraction of pages labeled `pymupdf` by the adapter. It measures route
  choice, not correctness.
- **Latency per page:** parser/extraction wall-clock seconds divided by page count, averaged by
  document. It excludes dataset generation and BM25 ranking. Compare only runs on similar
  hardware and dependency versions.

Scan difficulty is `low` for noise ≤ 0.2, `medium` for ≤ 0.5, and `high` otherwise; these
groups also vary in DPI and blur. The report includes a `not_scan` group for other documents.

## Superseded first Phase 2 test run

The first Phase 2 test-split run, using freeze commit
`caa7f35c2f46777eba1a690e0292dac1ea04fe39`, is **invalid as an assessment of the
routing design**: Docling's optional package/model artifacts were missing and Ollama was
unreachable. The run counted those pages as failures but could not measure the intended
backends. No routing or gate threshold was changed after seeing its test results. Its
report remains in `eval/results/phase2-parsing.md`, marked SUPERSEDED for audit. Phase 2b
requires `make preflight` to pass, dev-only tuning, and approval of a new freeze before
one replacement test run.

## Reproduce

From a clean clone with Python 3.11 or 3.12 and `uv`:

```bash
make setup
bash scripts/pull_font.sh
uv run python scripts/make_synthetic_docs.py
make eval
```

The font download is pinned to a Google Fonts revision. If network access is unavailable,
provide a local Noto Sans Devanagari font with `--font`. The generator never downloads a font
implicitly. `make eval` verifies every PDF hash against the manifest and writes
`eval/results/latest.json` and `latest.md` (both ignored by Git). The committed
`eval/results/baseline-phase1.md` is an actual run, including date, source commit, dirty-tree
flag, library versions, environment, model status, and separate dev/test tables.

For Phase 2b, `make preflight` verifies PyMuPDF, a real Docling parse using prefetched local
artifacts, localhost Ollama, the pulled `VISION_MODEL`, and a trivial model response.
`make eval` runs **dev only** using `eval/config/phase2b_dev.toml`. The runner refuses
`make eval-test` while the superseded freeze is active. After approval of a new freeze, it
will still refuse unless the freeze file is committed, the working tree is clean, preflight
passes, and no test page's initial route names an unavailable backend. The test report will
record that freeze hash, frozen values, vision model tag, and prompt version. The report
includes dev and test parsing results separately,
with category, language, and scan-difficulty breakdowns. It reports dev-only calibration as
Spearman rank correlation between page score and reference page accuracy, plus average accuracy
in score buckets `[0,.25)`, `[.25,.5)`, `[.5,.75)`, `[.75,1]`. Page accuracy is clipped
normalized-text similarity, averaged with page-level table F1 when a table is present. A
Calibration uses successfully parsed pages only and reports failed pages separately. It also
reports how many pages escalated and whether the reference page accuracy improved. Undefined
Spearman when all scores tie is reported as `n/a`, not zero. The dev-only threshold trials and
their measured effects are in `eval/TUNING_PHASE2B.md`.

The Phase 2 vision parser calls only local Ollama. Successful responses are cached under
`.cache/unmess/vlm` by raster-page SHA-256, model tag, and prompt version. No live service is
required for unit tests; the live Ollama smoke test is opt-in with
`uv run pytest -m integration`.
VLM-only text currently has a full-page bbox; it is coarse provenance, not precise highlighting.
The eval reports VLM attempts, cache hits, total VLM time, and pages per second.

## Limits

The documents deliberately use a small set of templates and fictional values. They are not a
representative sample of actual financial or personal records. The scan set varies degradation
parameters but does not capture every scanner artifact. Hindi appears as rasterized text, so
the cheap parser cannot extract it; its rendering depends on the pinned font and Pillow
version. Exact text and cell matching are strict. Bounding-box relevance rewards any geometric
intersection, not whether a reader would find the result useful. Reported numbers apply only
to this corpus, code revision, and environment.
