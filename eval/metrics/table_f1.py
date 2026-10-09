"""Cell-level table matching, including row/column spans."""

from collections import Counter

from unmess.models import Table


def _keys(tables: list[Table]) -> Counter[tuple[str, int, int, int, int, str]]:
    return Counter(
        (table.table_id, cell.row, cell.col, cell.row_span, cell.col_span, cell.text.strip())
        for table in tables
        for cell in table.cells
    )


def table_cell_f1(expected: list[Table], predicted: list[Table]) -> tuple[float, float, float]:
    """Return precision, recall, F1; empty/empty is perfect agreement."""
    gold, got = _keys(expected), _keys(predicted)
    if not gold and not got:
        return 1.0, 1.0, 1.0
    true_positive = sum((gold & got).values())
    precision = true_positive / sum(got.values()) if got else 0.0
    recall = true_positive / sum(gold.values()) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1
