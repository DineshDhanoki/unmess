from __future__ import annotations

from unmess.chunking.schema import ChunkRecord, StructuredTable, content_hash
from unmess.chunking.structure_aware import ChunkingConfig, chunk_pages
from unmess.chunking.tables import (
    decide_stitch,
    find_stitch_candidate,
    fragment_from_table,
    stitch_fragments,
)
from unmess.models import BBox, Block, Cell, Table
from unmess.parsing.base import ParsedPage
from unmess.store.dedupe import DedupeStore


def _box(page: int, x0: float, y0: float, x1: float, y1: float) -> BBox:
    return BBox(page=page, x0=x0, y0=y0, x1=x1, y1=y1)


def _table(page: int, table_id: str, rows: tuple[tuple[str, ...], ...], box: BBox) -> Table:
    cells = [
        Cell(row=row, col=col, text=text, bbox=box)
        for row, values in enumerate(rows)
        for col, text in enumerate(values)
    ]
    return Table(table_id=table_id, page_numbers=[page], cells=cells)


def _page(page: int, caption: str, table: Table, *, figure: bool = False) -> ParsedPage:
    blocks = [
        Block(
            block_id=f"h{page}",
            kind="heading",
            text="Ledger",
            bbox=_box(page, 0.1, 0.02, 0.4, 0.05),
        ),
        Block(
            block_id=f"c{page}",
            kind="caption",
            text=caption,
            bbox=_box(
                page,
                0.1,
                max(0.001, table.cells[0].bbox.y0 - 0.04),
                0.5,
                table.cells[0].bbox.y0 - 0.01,
            ),
        ),
    ]
    if figure:
        blocks.append(
            Block(
                block_id=f"f{page}",
                kind="figure",
                text="Figure",
                bbox=_box(page, 0.2, 0.08, 0.8, 0.25),
            )
        )
    blocks.append(Block(block_id=f"t{page}", kind="table", text="table", bbox=table.cells[0].bbox))
    return ParsedPage(page, "docling", blocks=blocks, tables=[table])


def _chunk(chunk_id: str, page: int, file_hash: str = "file") -> ChunkRecord:
    text = f"chunk {chunk_id}"
    return ChunkRecord(
        chunk_id=chunk_id,
        kind="text",
        markdown=text,
        file_hash=file_hash,
        page_hashes=(f"page-{page}",),
        page_numbers=(page,),
        bboxes=(_box(page, 0.1, 0.1, 0.2, 0.2),),
        section_path=(),
        parser_names=("docling",),
        content_hash=content_hash(text),
    )


def test_stitch_repeated_and_headerless_continuations() -> None:
    first_table = _table(1, "a", (("Item", "Qty"), ("A", "1")), _box(1, 0.1, 0.80, 0.9, 0.96))
    repeated = _table(2, "b", (("item.", "QTY"), ("B", "2")), _box(2, 0.1, 0.05, 0.9, 0.20))
    headerless = _table(2, "c", (("B", "2"), ("C", "3")), _box(2, 0.1, 0.05, 0.9, 0.20))
    first = fragment_from_table(_page(1, "Ledger (part 1)", first_table), first_table)

    second = fragment_from_table(_page(2, "Ledger (continued)", repeated), repeated)
    decision = decide_stitch(first, second)
    assert decision.should_stitch and decision.repeated_header
    assert stitch_fragments(first, second).structured.rows == (("A", "1"), ("B", "2"))

    second = fragment_from_table(_page(2, "Ledger", headerless), headerless)
    decision = decide_stitch(first, second)
    assert decision.should_stitch and not decision.repeated_header
    assert stitch_fragments(first, second).structured.rows == (("A", "1"), ("B", "2"), ("C", "3"))


def test_stitch_vetoes_midpage_geometry_and_figure_discontinuity() -> None:
    rows = (("Item", "Qty"), ("A", "1"))
    first_table = _table(1, "a", rows, _box(1, 0.1, 0.80, 0.9, 0.96))
    first = fragment_from_table(_page(1, "Ledger", first_table), first_table)

    offset = _table(2, "b", rows, _box(2, 0.3, 0.05, 0.7, 0.20))
    assert not decide_stitch(
        first, fragment_from_table(_page(2, "Ledger", offset), offset)
    ).should_stitch

    midpage = _table(1, "m", rows, _box(1, 0.1, 0.35, 0.9, 0.50))
    mid = fragment_from_table(_page(1, "Ledger", midpage), midpage)
    top = _table(2, "t", rows, _box(2, 0.1, 0.05, 0.9, 0.20))
    assert not decide_stitch(mid, fragment_from_table(_page(2, "Ledger", top), top)).should_stitch

    after_figure = _table(2, "f", rows, _box(2, 0.1, 0.35, 0.9, 0.50))
    fragment = fragment_from_table(_page(2, "Notes", after_figure, figure=True), after_figure)
    assert not decide_stitch(first, fragment).should_stitch


def test_candidate_search_skips_non_table_shape_and_prunes_sparse_column() -> None:
    first_table = _table(
        1, "a", (("Item", "Qty", "Amount"), ("A", "1", "10")), _box(1, 0.1, 0.80, 0.9, 0.96)
    )
    first = fragment_from_table(_page(1, "Ledger", first_table), first_table)
    picture_shape = _table(2, "picture", (("figure",),), _box(2, 0.2, 0.08, 0.8, 0.25))
    sparse = _table(
        2,
        "b",
        (("Item", "Qty", "noise", "Amount"), ("B", "2", "", "20")),
        _box(2, 0.1, 0.35, 0.9, 0.50),
    )
    following = (
        fragment_from_table(_page(2, "Figure", picture_shape), picture_shape),
        fragment_from_table(_page(2, "Ledger (continued)", sparse, figure=True), sparse),
    )

    match = find_stitch_candidate(first, following)
    assert match is not None
    assert match[0] == 1
    assert len(following[1].structured.columns) == 3


def test_structure_chunker_keeps_table_atomic_and_attaches_list() -> None:
    box = _box(1, 0.1, 0.5, 0.9, 0.8)
    table = _table(1, "a", (("Item", "Qty"), ("A", "1")), box)
    blocks = [
        Block(block_id="h", kind="heading", text="Section", bbox=_box(1, 0.1, 0.05, 0.5, 0.1)),
        Block(
            block_id="p",
            kind="paragraph",
            text="Parent paragraph",
            bbox=_box(1, 0.1, 0.12, 0.8, 0.2),
        ),
        Block(
            block_id="l",
            kind="list",
            text="- attached item",
            bbox=_box(1, 0.1, 0.21, 0.8, 0.28),
            parent_id="p",
        ),
        Block(block_id="t", kind="table", text="table", bbox=box),
    ]
    chunks = chunk_pages(
        [ParsedPage(1, "docling", blocks=blocks, tables=[table])],
        file_hash="file",
        page_hashes={1: "page"},
        config=ChunkingConfig(target_tokens=4, overlap_tokens=0),
    )
    text_chunks = [chunk for chunk in chunks if chunk.kind == "text"]
    table_chunks = [chunk for chunk in chunks if chunk.kind == "table"]
    assert len(text_chunks) == 1
    assert "Parent paragraph\n- attached item" in text_chunks[0].markdown
    assert text_chunks[0].section_path == ("Section",)
    assert len(table_chunks) == 1
    assert isinstance(table_chunks[0].structured_table, StructuredTable)
    assert "| Item | Qty |" in table_chunks[0].markdown


def test_dedupe_noop_and_changed_page_only() -> None:
    store = DedupeStore()
    initial = store.plan("doc", "file-1", {1: "page-1", 2: "page-2"})
    store.commit(
        "doc", "file-1", {1: "page-1", 2: "page-2"}, [_chunk("a", 1), _chunk("b", 2)], initial
    )

    assert store.plan("doc", "file-1", {1: "page-1", 2: "page-2"}).unchanged
    changed = store.plan("doc", "file-2", {1: "page-1", 2: "page-2-new"})
    assert changed.changed_pages == (2,)
    assert changed.remove_chunk_ids == ("b",)
    store.commit("doc", "file-2", {1: "page-1", 2: "page-2-new"}, [_chunk("c", 2)], changed)
    assert tuple(chunk.chunk_id for chunk in store.chunks("doc")) == ("a", "c")
