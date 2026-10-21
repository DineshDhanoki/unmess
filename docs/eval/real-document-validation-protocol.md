# Privacy-safe real-document validation protocol

## Purpose and boundary

The committed evaluation corpus is synthetic. It is the only source for the
current DEV claims in this repository. This protocol describes a future,
opt-in way to validate Unmess against real documents without putting source
documents, extracted text, or personal data in Git.

Following this protocol does **not** turn a local trial into a benchmark. A
real-document result must be reported separately from the synthetic results,
with its collection and limitations stated alongside it.

## Before collecting anything

- Obtain written permission from the document owner and, where applicable,
  the organisation that controls the data. Permission must cover local
  processing, annotation, and the aggregate results that may be published.
- Exclude documents containing credentials, government identifiers, health
  records, payment-card data, legal files under privilege, or data subject to
  a contract or regulation that prohibits this use.
- Do not solicit documents from people who may feel pressured to provide
  them. Participation must be voluntary and may be withdrawn at any time.
- Record the consent date, allowed purpose, and retention deadline in a
  **local, untracked** log. Do not put names, email addresses, document
  names, or consent records in the repository.

## Local-only handling

1. Process documents only on an encrypted machine or encrypted volume that
   the contributor controls. Keep the pipeline offline except for explicitly
   approved localhost services.
2. Disable cloud backup, shared folders, telemetry uploads, and external
   model/API calls for the trial. Use local models and local storage only.
3. Store inputs, parser caches, annotations, logs, and exported reports in a
   dedicated directory outside the checkout. Add that directory to the local
   global Git ignore if necessary.
4. Redact direct identifiers before processing where practical. If a document
   cannot be safely redacted, do not use it.
5. Never paste raw text, page images, screenshots, bounding boxes tied to a
   recognisable page, error traces containing text, or document hashes into an
   issue, pull request, commit, or public report.

## Retention and deletion

Use the shortest practical retention period and record its end date locally.
When a trial ends or consent is withdrawn, delete the original documents,
derived images, OCR/parser caches, embeddings, vector databases, temporary
files, and local annotations. Empty the system trash if it contains these
files. Keep only a de-identified aggregate summary if publication was
permitted.

## Annotation and split design

Give each locally stored document an opaque ID such as `trial-014`; keep the
ID-to-file mapping outside the repository. Annotations should describe only
the evaluation target: for example, a page count, whether a table continues,
or a pass/fail label. Do not copy source cell values or free-form text into the
annotation file.

Assign documents to train, DEV, and test before tuning. Keep document families
together: pages from one document, revisions of the same document, and
near-duplicates must never cross splits. Tune only on the local DEV split.
Keep the local test labels and results unread until the configuration and
evaluation command are frozen. A contributor should retain a local record of
the split seed, code revision, model versions, and hardware, but must not
commit document-level identifiers or content.

## Publication rules

Published material may contain only aggregate, de-identified metrics and
methodology. State the number of documents/pages, broad document categories,
consent basis, exclusions, local-only processing controls, split policy,
software revision, hardware, and failures. Do not publish a metric for a
group small enough to make a participant or document identifiable; combine or
withhold it instead.

Every report must state that the repository's synthetic DEV results are
separate. It must not combine private-trial metrics with the committed
synthetic benchmark or claim generalisation beyond the voluntary sample.

## Synthetic-only example

The following is safe to commit because it contains no real document data:

```json
{
  "trial_id": "synthetic-example-01",
  "source": "synthetic fixture only",
  "split": "dev",
  "page_count": 2,
  "table_continuation": true,
  "result": "pass"
}
```

For a real local trial, keep the same kind of record outside Git, replace the
source field with a local consent-log reference, and omit any file name or
source text.

## Contributor checklist

- [ ] I have documented valid permission and a retention deadline locally.
- [ ] The documents and all derived data are outside the repository and are
      excluded from sync and backup services.
- [ ] I use no external model, API, or cloud storage for this trial.
- [ ] I redacted data where possible and rejected disallowed document types.
- [ ] I assigned whole document families to one split before tuning.
- [ ] I will report only aggregate, de-identified results with failures.
- [ ] I will clearly separate any local real-document result from synthetic
      DEV claims.
- [ ] I have a plan to delete originals and derived artifacts at the retention
      deadline or on withdrawal of consent.
