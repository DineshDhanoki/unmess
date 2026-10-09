"""Table boundary integrity."""

from unmess.models import Chunk, Table


def table_split_rate(tables: list[Table], chunks: list[Chunk]) -> float | None:
    if not tables:
        return None
    split = 0
    for table in tables:
        cell_texts = [cell.text for cell in table.cells if cell.text.strip()]
        if not any(all(text in chunk.text for text in cell_texts) for chunk in chunks):
            split += 1
    return split / len(tables)
