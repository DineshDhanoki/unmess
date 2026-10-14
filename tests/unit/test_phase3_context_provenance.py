from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from unmess.chunking.contextual import ContextConfig, add_context
from unmess.chunking.schema import ChunkRecord, content_hash
from unmess.models import BBox
from unmess.provenance.citations import render_highlight, source_region


def _chunk() -> ChunkRecord:
    text = "Synthetic citation text"
    return ChunkRecord(
        chunk_id="chunk",
        kind="text",
        markdown=text,
        file_hash="abc",
        page_hashes=("page",),
        page_numbers=(1,),
        bboxes=(BBox(page=1, x0=0.1, y0=0.1, x1=0.5, y1=0.3),),
        section_path=(),
        parser_names=("pymupdf",),
        content_hash=content_hash(text),
    )


def test_context_is_off_by_default_and_reads_hash_cache(tmp_path: Path) -> None:
    chunk = _chunk()
    assert add_context(chunk) is chunk
    cache = tmp_path / f"{chunk.content_hash}.json"
    cache.write_text(json.dumps({"context": "A cached factual line."}), encoding="utf-8")
    contextualized = add_context(chunk, ContextConfig(enabled=True, cache_dir=tmp_path))
    assert contextualized.context == "A cached factual line."


def test_source_region_and_highlight_renderer(tmp_path: Path) -> None:
    pdf = tmp_path / "source.pdf"
    document = pymupdf.open()
    document.new_page(width=200, height=100)
    document.save(pdf)
    document.close()

    region = source_region(_chunk())
    image = render_highlight(pdf, region, 1, dpi=72)

    assert region.file_hash == "abc"
    assert image.size == (200, 100)
    assert image.getpixel((20, 10)) != (255, 255, 255)
