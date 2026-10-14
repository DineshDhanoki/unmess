"""Resolve a chunk citation and render its normalized source regions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from unmess.chunking.schema import ChunkRecord
from unmess.models import BBox


@dataclass(frozen=True)
class SourceRegion:
    file_hash: str
    page_numbers: tuple[int, ...]
    bboxes: tuple[BBox, ...]


def source_region(chunk: ChunkRecord) -> SourceRegion:
    return SourceRegion(chunk.file_hash, chunk.page_numbers, chunk.bboxes)


def render_highlight(
    pdf: Path,
    region: SourceRegion,
    page_number: int,
    *,
    dpi: int = 144,
) -> Image.Image:
    if page_number not in region.page_numbers:
        raise ValueError("requested page is outside the source region")
    with pymupdf.open(pdf) as document:
        page = document[page_number - 1]
        pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    draw = ImageDraw.Draw(image, "RGBA")
    for box in region.bboxes:
        if box.page != page_number:
            continue
        coordinates = (
            round(box.x0 * image.width),
            round(box.y0 * image.height),
            round(box.x1 * image.width),
            round(box.y1 * image.height),
        )
        draw.rectangle(coordinates, fill=(255, 220, 0, 65), outline=(230, 120, 0, 255), width=3)
    return image
