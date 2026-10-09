"""Pure feature calculations and a thin PyMuPDF observation adapter."""

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pymupdf
from PIL import Image


@dataclass(frozen=True)
class PageFeatures:
    embedded_text: str
    embedded_text_density: float
    image_coverage: float
    scan_likelihood: float
    table_likelihood: float
    skew_degrees: float
    garbled_character_ratio: float
    dominant_script: str
    layout_complexity: float


def text_density(text: str, width: float, height: float) -> float:
    """Non-space characters per 1,000 PDF points squared, clipped to 0-1."""
    if width <= 0 or height <= 0:
        raise ValueError("page dimensions must be positive")
    return min(1.0, sum(not char.isspace() for char in text) * 1000 / (width * height))


def area_coverage(
    rectangles: Sequence[tuple[float, float, float, float]], width: float, height: float
) -> float:
    """Approximate image coverage; overlapping images are clipped to one page."""
    if width <= 0 or height <= 0:
        raise ValueError("page dimensions must be positive")
    area = sum(
        max(0.0, min(width, x1) - max(0.0, x0)) * max(0.0, min(height, y1) - max(0.0, y0))
        for x0, y0, x1, y1 in rectangles
    )
    return min(1.0, area / (width * height))


def garbled_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(
        char == "\ufffd" or unicodedata.category(char) in {"Cc", "Cs", "Co", "Cn"}
        for char in text
        if not char.isspace()
    )
    visible = sum(not char.isspace() for char in text)
    return bad / visible if visible else 0.0


def dominant_script(text: str) -> str:
    devanagari = sum("\u0900" <= char <= "\u097f" for char in text)
    latin = sum("A" <= char <= "Z" or "a" <= char <= "z" for char in text)
    return "Devanagari" if devanagari > latin else "Latin" if latin else "unknown"


def table_likelihood(text: str, horizontal_lines: int, aligned_columns: int) -> float:
    cues = sum(word in text.casefold() for word in ("item", "qty", "amount", "cgst", "sgst"))
    return min(1.0, 0.13 * cues + 0.07 * horizontal_lines + 0.10 * aligned_columns)


def scan_likelihood(density: float, image_coverage: float) -> float:
    return min(1.0, image_coverage * (1.0 - density) + max(0.0, 0.12 - density) * 2)


def layout_complexity(block_count: int, columns: int, table_score: float) -> float:
    return min(
        1.0, max(0, columns - 1) * 0.30 + max(0, block_count - 4) * 0.05 + table_score * 0.45
    )


def estimate_skew(gray: Image.Image) -> float:
    """Pick the angle with the strongest horizontal text-row projection."""
    gray = gray.convert("L")
    gray.thumbnail((240, 240))
    best_angle, best_score = 0.0, -math.inf
    for angle in range(-8, 9, 2):
        rotated = gray.rotate(-angle, resample=Image.Resampling.BILINEAR, fillcolor=255)
        pixels = rotated.load()
        assert pixels is not None
        row_counts = [
            sum(cast(int, pixels[x, y]) < 130 for x in range(rotated.width))
            for y in range(rotated.height)
        ]
        mean = sum(row_counts) / max(1, len(row_counts))
        score = sum((count - mean) ** 2 for count in row_counts)
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def from_observations(
    text: str,
    width: float,
    height: float,
    image_rectangles: Sequence[tuple[float, float, float, float]],
    horizontal_lines: int,
    aligned_columns: int,
    block_count: int,
    skew_degrees: float,
) -> PageFeatures:
    density = text_density(text, width, height)
    coverage = area_coverage(image_rectangles, width, height)
    table_score = table_likelihood(text, horizontal_lines, aligned_columns)
    return PageFeatures(
        embedded_text=text,
        embedded_text_density=density,
        image_coverage=coverage,
        scan_likelihood=scan_likelihood(density, coverage),
        table_likelihood=table_score,
        skew_degrees=skew_degrees,
        garbled_character_ratio=garbled_ratio(text),
        dominant_script=dominant_script(text),
        layout_complexity=layout_complexity(block_count, aligned_columns, table_score),
    )


def inspect_page(pdf: Path, page_number: int) -> PageFeatures:
    """Collect observations; feature calculations remain independently testable."""
    with pymupdf.open(pdf) as document:
        page = document[page_number - 1]
        text = page.get_text("text")
        blocks = page.get_text("blocks")
        image_rects = [
            (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
            for image in page.get_images(full=True)
            for rect in page.get_image_rects(image[0])
        ]
        drawings = page.get_drawings()
        horizontal = sum(
            item[0] == "l" and abs(item[1].y - item[2].y) < 2
            for drawing in drawings
            for item in drawing["items"]
        )
        words = page.get_text("words")
        buckets: dict[int, int] = {}
        for word in words:
            column = round(float(word[0]) / 25)
            buckets[column] = buckets.get(column, 0) + 1
        columns = sum(count >= 3 for count in buckets.values())
        skew = 0.0
        if image_rects:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(0.3, 0.3), colorspace=pymupdf.csGRAY)
            skew = estimate_skew(Image.frombytes("L", (pix.width, pix.height), pix.samples))
        return from_observations(
            text,
            page.rect.width,
            page.rect.height,
            image_rects,
            horizontal,
            columns,
            len(blocks),
            skew,
        )
