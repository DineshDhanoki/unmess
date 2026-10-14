# Phase 3 ingestion architecture

Phase 3 is additive to the frozen Phase 2 pipeline. Existing parsers and the router still emit
`ParsedPage`; the new layer consumes those records without changing parsing, routing, scoring,
gates, or thresholds.

The chunk schema stores Markdown, optional structured table JSON, section path, source file hash,
page hashes, parser names, page numbers, and normalized bounding boxes. Structure-aware chunking
updates the active heading path, keeps list and caption children with their parent block, overlaps
only whole blocks, and emits each table as an atomic chunk. Cross-page table fragments may be
combined before chunk construction.

Stitching is deliberately conservative. It considers tables on consecutive pages, requires equal
column count, a first fragment near the page end, compatible horizontal geometry, and an explicit
continuity signal. A second fragment below the normal page-start band is eligible only when its
table identity remains consistent despite intervening content. Header similarity, geometry
tolerance, and the page-edge band are the only tunable parameters. Repeated headers are removed;
headerless rows are retained; row indices continue across source pages.

Citation lookup returns the file hash, pages, and normalized boxes carried by a chunk. Rendering
rasterizes only a requested cited page and overlays those boxes. The in-memory dedupe contract
hashes files, pages, and chunks: an unchanged ingest is a no-op, while a changed page invalidates
only chunks citing that page.

Optional contextualization is disabled by default. When enabled, it calls the configured local
Ollama text model and caches the one-line result by chunk content hash. Document content is not
sent to a remote service.
