"""Atomic table chunks and conservative cross-page stitching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from unmess.chunking.schema import StructuredTable
from unmess.models import BBox, Block, Table
from unmess.parsing.base import ParsedPage


@dataclass(frozen=True)
class StitchConfig:
    header_similarity: float = 0.72
    geometry_tolerance: float = 0.08
    page_edge_band: float = 0.20


DEFAULT_STITCH_CONFIG = StitchConfig()


@dataclass(frozen=True)
class TableFragment:
    table: Table
    markdown: str
    structured: StructuredTable
    bbox: BBox
    caption: str
    section_path: tuple[str, ...]
    intervening_content: bool = False


@dataclass(frozen=True)
class StitchDecision:
    should_stitch: bool
    repeated_header: bool
    reasons: tuple[str, ...]


def _matrix(table: Table) -> tuple[tuple[str, ...], ...]:
    row_count = max(cell.row + cell.row_span for cell in table.cells)
    column_count = max(cell.col + cell.col_span for cell in table.cells)
    rows = [["" for _ in range(column_count)] for _ in range(row_count)]
    for cell in table.cells:
        rows[cell.row][cell.col] = cell.text.strip()
    populated_rows = [
        {row_index for row_index, row in enumerate(rows) if row[column_index]}
        for column_index in range(column_count)
    ]
    sparse_leading_only = {
        column_index
        for column_index, occupied in enumerate(populated_rows)
        if occupied == {0} and any(len(other) > 1 for other in populated_rows)
    }
    if sparse_leading_only and column_count - len(sparse_leading_only) >= 2:
        rows = [
            [
                value
                for column_index, value in enumerate(row)
                if column_index not in sparse_leading_only
            ]
            for row in rows
        ]
    return tuple(tuple(row) for row in rows)


def _markdown(columns: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join((header, divider, *body))


def _captioned_markdown(
    caption: str, columns: tuple[str, ...], rows: tuple[tuple[str, ...], ...]
) -> str:
    table = _markdown(columns, rows)
    return f"{caption}\n\n{table}" if caption else table


def _table_bbox(table: Table) -> BBox:
    boxes = [cell.bbox for cell in table.cells]
    page = table.page_numbers[0]
    return BBox(
        page=page,
        x0=min(box.x0 for box in boxes),
        y0=min(box.y0 for box in boxes),
        x1=max(box.x1 for box in boxes),
        y1=max(box.y1 for box in boxes),
    )


def _normalized_words(text: str) -> tuple[str, ...]:
    clean = text.casefold().replace("ltem", "item").replace("arnount", "amount")
    return tuple(re.findall(r"[a-z0-9]+", clean))


def _identity(text: str) -> str:
    ignored = {"continued", "continue", "part", "page", "synthetic"}
    words = [word for word in _normalized_words(text) if word not in ignored and not word.isdigit()]
    return " ".join(dict.fromkeys(words))


def _similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_text = " ".join(word for value in left for word in _normalized_words(value))
    right_text = " ".join(word for value in right for word in _normalized_words(value))
    return SequenceMatcher(None, left_text, right_text).ratio()


def _nearby_context(blocks: list[Block], bbox: BBox) -> tuple[str, tuple[str, ...], bool]:
    preceding = [
        block
        for block in blocks
        if block.kind != "table"
        and block.bbox.page == bbox.page
        and block.bbox.y1 <= bbox.y0 + 0.03
    ]
    preceding.sort(key=lambda block: block.bbox.y1)
    caption = preceding[-1].text.strip() if preceding else ""
    headings = [block.text.strip() for block in preceding if block.kind == "heading"]
    section_path = tuple(headings[-2:]) or ((caption,) if caption else ())
    return caption, section_path, bool(preceding)


def fragment_from_table(page: ParsedPage, table: Table) -> TableFragment:
    matrix = _matrix(table)
    columns = matrix[0]
    rows = matrix[1:]
    bbox = _table_bbox(table)
    caption, section_path, intervening_content = _nearby_context(page.blocks, bbox)
    structured = StructuredTable(
        columns=columns,
        rows=rows,
        row_indices=tuple(range(len(rows))),
        source_table_ids=(table.table_id,),
    )
    return TableFragment(
        table=table,
        markdown=_captioned_markdown(caption, columns, rows),
        structured=structured,
        bbox=bbox,
        caption=caption,
        section_path=section_path,
        intervening_content=intervening_content,
    )


def fragments_from_pages(pages: list[ParsedPage]) -> list[TableFragment]:
    return [fragment_from_table(page, table) for page in pages for table in page.tables]


def _geometry_matches(first: BBox, second: BBox, tolerance: float) -> bool:
    return (
        abs(first.x0 - second.x0) <= tolerance
        and abs(first.x1 - second.x1) <= tolerance
        and abs((first.x1 - first.x0) - (second.x1 - second.x0)) <= tolerance
    )


def decide_stitch(
    first: TableFragment,
    second: TableFragment,
    config: StitchConfig = DEFAULT_STITCH_CONFIG,
) -> StitchDecision:
    reasons: list[str] = []
    if second.bbox.page != first.bbox.page + 1:
        return StitchDecision(False, False, ("not_consecutive_pages",))
    if len(first.structured.columns) != len(second.structured.columns):
        return StitchDecision(False, False, ("column_count_mismatch",))
    if first.bbox.y1 < 1.0 - config.page_edge_band:
        return StitchDecision(False, False, ("first_table_not_near_page_end",))
    at_start = second.bbox.y0 <= config.page_edge_band
    if not at_start and not second.intervening_content:
        return StitchDecision(False, False, ("second_table_not_near_page_start",))
    if not _geometry_matches(first.bbox, second.bbox, config.geometry_tolerance):
        return StitchDecision(False, False, ("geometry_mismatch",))
    reasons.append("geometry_matches")

    header_score = _similarity(first.structured.columns, second.structured.columns)
    repeated_header = header_score >= config.header_similarity
    if repeated_header:
        reasons.append("header_matches")

    first_identity = _identity(first.caption)
    second_identity = _identity(second.caption)
    identity_matches = bool(first_identity and first_identity == second_identity)
    explicit_continuation = "continued" in _normalized_words(second.caption)
    if identity_matches:
        reasons.append("caption_identity_matches")
    if explicit_continuation:
        reasons.append("explicit_continuation")
    if first_identity and second_identity and not identity_matches and not explicit_continuation:
        return StitchDecision(False, repeated_header, (*reasons, "caption_identity_mismatch"))
    if not at_start and not identity_matches:
        return StitchDecision(
            False, repeated_header, (*reasons, "intervening_content_discontinuity")
        )
    if not (repeated_header or explicit_continuation or identity_matches):
        return StitchDecision(False, repeated_header, (*reasons, "no_continuity_signal"))
    return StitchDecision(True, repeated_header, tuple(reasons))


def find_stitch_candidate(
    first: TableFragment,
    following: tuple[TableFragment, ...] | list[TableFragment],
    config: StitchConfig = DEFAULT_STITCH_CONFIG,
) -> tuple[int, StitchDecision] | None:
    for index, candidate in enumerate(following):
        if candidate.bbox.page > first.bbox.page + 1:
            break
        decision = decide_stitch(first, candidate, config)
        if decision.should_stitch:
            return index, decision
    return None


def stitch_fragments(
    first: TableFragment,
    second: TableFragment,
    config: StitchConfig = DEFAULT_STITCH_CONFIG,
) -> TableFragment:
    decision = decide_stitch(first, second, config)
    if not decision.should_stitch:
        raise ValueError("table fragments do not satisfy stitching rules")
    second_rows = (
        second.structured.rows
        if decision.repeated_header
        else (second.structured.columns, *second.structured.rows)
    )
    rows = (*first.structured.rows, *second_rows)
    cells = list(first.table.cells)
    first_row_count = len(first.structured.rows) + 1
    for cell in second.table.cells:
        if decision.repeated_header and cell.row == 0:
            continue
        row_offset = first_row_count - (1 if decision.repeated_header else 0)
        cells.append(cell.model_copy(update={"row": cell.row + row_offset}))
    table = Table(
        table_id=f"{first.table.table_id}+{second.table.table_id}",
        page_numbers=[*first.table.page_numbers, *second.table.page_numbers],
        cells=cells,
        has_merged_cells=any(cell.row_span > 1 or cell.col_span > 1 for cell in cells),
        spans_pages=True,
    )
    structured = StructuredTable(
        columns=first.structured.columns,
        rows=rows,
        row_indices=tuple(range(len(rows))),
        source_table_ids=(*first.structured.source_table_ids, *second.structured.source_table_ids),
    )
    return TableFragment(
        table=table,
        markdown=_captioned_markdown(first.caption, structured.columns, structured.rows),
        structured=structured,
        bbox=first.bbox,
        caption=first.caption,
        section_path=first.section_path,
        intervening_content=False,
    )


def stitch_document_tables(
    pages: list[ParsedPage], config: StitchConfig = DEFAULT_STITCH_CONFIG
) -> tuple[list[TableFragment], list[StitchDecision]]:
    fragments = fragments_from_pages(pages)
    output: list[TableFragment] = []
    decisions: list[StitchDecision] = []
    consumed: set[int] = set()
    for index, fragment in enumerate(fragments):
        if index in consumed:
            continue
        match = find_stitch_candidate(fragment, fragments[index + 1 :], config)
        if match is None:
            output.append(fragment)
            continue
        offset, decision = match
        candidate_index = index + 1 + offset
        decisions.append(decision)
        consumed.add(candidate_index)
        output.append(stitch_fragments(fragment, fragments[candidate_index], config))
    return output, decisions
