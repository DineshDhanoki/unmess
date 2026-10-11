"""Cell-level table matching, allowing a missing leading row without erasing credit."""

from collections import Counter

from unmess.models import Table

CellKey = tuple[str, int, int, int, int, str]


def _keys(tables: list[Table], shifts: dict[str, int] | None = None) -> Counter[CellKey]:
    return Counter(
        (
            table.table_id,
            cell.row + (shifts or {}).get(table.table_id, 0),
            cell.col,
            cell.row_span,
            cell.col_span,
            cell.text.strip(),
        )
        for table in tables
        for cell in table.cells
    )


def _best_row_shifts(expected: list[Table], predicted: list[Table]) -> dict[str, int]:
    """Align row origins per table, but never forgive missing text or wrong spans."""
    shifts: dict[str, int] = {}
    ids = {table.table_id for table in expected} & {table.table_id for table in predicted}
    for table_id in ids:
        gold = [cell for table in expected if table.table_id == table_id for cell in table.cells]
        got = [cell for table in predicted if table.table_id == table_id for cell in table.cells]
        candidate_shifts = {0} | {
            reference.row - candidate.row
            for reference in gold
            for candidate in got
            if (
                reference.col,
                reference.row_span,
                reference.col_span,
                reference.text.strip(),
            )
            == (
                candidate.col,
                candidate.row_span,
                candidate.col_span,
                candidate.text.strip(),
            )
        }
        gold_keys = _keys([table for table in expected if table.table_id == table_id])
        shifts[table_id] = max(
            sorted(candidate_shifts),
            key=lambda shift: sum(
                (
                    gold_keys
                    & _keys(
                        [table for table in predicted if table.table_id == table_id],
                        {table_id: shift},
                    )
                ).values()
            ),
        )
    return shifts


def table_cell_f1(expected: list[Table], predicted: list[Table]) -> tuple[float, float, float]:
    """Return precision, recall, F1; empty/empty is perfect agreement."""
    gold, got = _keys(expected), _keys(predicted, _best_row_shifts(expected, predicted))
    if not gold and not got:
        return 1.0, 1.0, 1.0
    true_positive = sum((gold & got).values())
    precision = true_positive / sum(got.values()) if got else 0.0
    recall = true_positive / sum(gold.values()) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
