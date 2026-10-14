"""Heading-aware chunking over parser-independent page blocks."""

from __future__ import annotations

from dataclasses import dataclass

from unmess.chunking.schema import ChunkRecord, content_hash
from unmess.chunking.tables import DEFAULT_STITCH_CONFIG, StitchConfig, stitch_document_tables
from unmess.models import BBox, Block
from unmess.parsing.base import ParsedPage


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 600
    overlap_tokens: int = 80

    def __post_init__(self) -> None:
        if self.target_tokens <= 0:
            raise ValueError("target tokens must be positive")
        if self.overlap_tokens < 0 or self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap must be non-negative and smaller than target")


DEFAULT_CHUNKING_CONFIG = ChunkingConfig()


@dataclass(frozen=True)
class _BlockGroup:
    blocks: tuple[Block, ...]
    section_path: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(block.text.strip() for block in self.blocks if block.text.strip())

    @property
    def tokens(self) -> int:
        return max(1, len(self.text.split()))


def _groups(pages: list[ParsedPage]) -> list[_BlockGroup]:
    groups: list[_BlockGroup] = []
    section: list[str] = []
    for page in pages:
        blocks = sorted(page.blocks, key=lambda block: (block.bbox.y0, block.bbox.x0))
        by_id = {block.block_id: block for block in blocks}
        consumed: set[str] = set()
        for index, block in enumerate(blocks):
            if block.block_id in consumed or block.kind in {"table", "figure"}:
                continue
            if block.kind == "heading":
                section = [block.text.strip()]
                consumed.add(block.block_id)
                continue
            if block.kind == "caption" and any(
                candidate.kind == "table"
                and candidate.bbox.page == block.bbox.page
                and block.bbox.y1 <= candidate.bbox.y0 + 0.03
                and candidate.bbox.y0 - block.bbox.y1 <= 0.08
                for candidate in blocks
            ):
                consumed.add(block.block_id)
                continue
            attached = [block]
            children = [candidate for candidate in blocks if candidate.parent_id == block.block_id]
            attached.extend(
                candidate for candidate in children if candidate.kind in {"list", "caption"}
            )
            consumed.update(candidate.block_id for candidate in attached)
            if block.kind in {"list", "caption"} and block.parent_id is None and groups:
                previous = groups[-1]
                groups[-1] = _BlockGroup((*previous.blocks, block), previous.section_path)
                consumed.add(block.block_id)
                continue
            if block.parent_id and block.parent_id in by_id:
                continue
            groups.append(_BlockGroup(tuple(attached), tuple(section)))
            if index == len(blocks) - 1:
                consumed.add(block.block_id)
    return groups


def _page_boxes(boxes: list[BBox]) -> tuple[BBox, ...]:
    output: list[BBox] = []
    for page in sorted({box.page for box in boxes}):
        page_boxes = [box for box in boxes if box.page == page]
        output.append(
            BBox(
                page=page,
                x0=min(box.x0 for box in page_boxes),
                y0=min(box.y0 for box in page_boxes),
                x1=max(box.x1 for box in page_boxes),
                y1=max(box.y1 for box in page_boxes),
            )
        )
    return tuple(output)


def _text_chunk(
    groups: list[_BlockGroup],
    file_hash: str,
    page_hashes: dict[int, str],
    parsers: dict[int, str],
) -> ChunkRecord:
    text = "\n\n".join(group.text for group in groups)
    boxes = _page_boxes([block.bbox for group in groups for block in group.blocks])
    pages = tuple(box.page for box in boxes)
    digest = content_hash(text)
    return ChunkRecord(
        chunk_id=f"text-{digest[:20]}",
        kind="text",
        markdown=text,
        file_hash=file_hash,
        page_hashes=tuple(page_hashes[page] for page in pages),
        page_numbers=pages,
        bboxes=boxes,
        section_path=groups[0].section_path,
        parser_names=tuple(dict.fromkeys(parsers[page] for page in pages)),
        content_hash=digest,
        block_ids=tuple(block.block_id for group in groups for block in group.blocks),
    )


def chunk_pages(
    pages: list[ParsedPage],
    *,
    file_hash: str,
    page_hashes: dict[int, str],
    config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    stitch_config: StitchConfig = DEFAULT_STITCH_CONFIG,
) -> list[ChunkRecord]:
    parsers = {page.page_number: page.parser_name for page in pages}
    chunks: list[ChunkRecord] = []
    current: list[_BlockGroup] = []
    current_tokens = 0
    for group in _groups(pages):
        if current and current_tokens + group.tokens > config.target_tokens:
            chunks.append(_text_chunk(current, file_hash, page_hashes, parsers))
            overlap: list[_BlockGroup] = []
            overlap_tokens = 0
            for previous in reversed(current):
                if overlap_tokens + previous.tokens > config.overlap_tokens:
                    break
                overlap.insert(0, previous)
                overlap_tokens += previous.tokens
            current = overlap
            current_tokens = overlap_tokens
        current.append(group)
        current_tokens += group.tokens
    if current:
        chunks.append(_text_chunk(current, file_hash, page_hashes, parsers))

    tables, _decisions = stitch_document_tables(pages, stitch_config)
    for fragment in tables:
        boxes = _page_boxes([cell.bbox for cell in fragment.table.cells])
        page_numbers = tuple(box.page for box in boxes)
        digest = content_hash(fragment.markdown + fragment.structured.as_json())
        chunks.append(
            ChunkRecord(
                chunk_id=f"table-{digest[:20]}",
                kind="table",
                markdown=fragment.markdown,
                file_hash=file_hash,
                page_hashes=tuple(page_hashes[page] for page in page_numbers),
                page_numbers=page_numbers,
                bboxes=boxes,
                section_path=fragment.section_path,
                parser_names=tuple(dict.fromkeys(parsers[page] for page in page_numbers)),
                content_hash=digest,
                structured_table=fragment.structured,
            )
        )
    return sorted(chunks, key=lambda chunk: (chunk.page_numbers[0], chunk.kind, chunk.chunk_id))
