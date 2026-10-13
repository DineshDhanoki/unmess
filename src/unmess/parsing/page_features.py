"""Pure feature calculations and a thin PyMuPDF observation adapter."""

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pymupdf
from PIL import Image, ImageChops, ImageDraw


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
    text_ink_alignment: float = 1.0
    uncovered_ink_ratio: float = 0.0
    rendered_noise_score: float = 0.0
    previous_page_table_likelihood: float = 0.0


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


def character_plausibility(text: str) -> float:
    """Penalize implausibly vowelless long Latin tokens, not specific corruption strings."""
    tokens = [word for word in text.casefold().split() if len(word) >= 6 and word.isalpha()]
    if not tokens:
        return 1.0
    plausible = sum(
        any(letter in word for letter in "aeiou") or any("\u0900" <= c <= "\u097f" for c in word)
        for word in tokens
    )
    return plausible / len(tokens)


def script_plausibility(text: str) -> float:
    """Most letters should belong to a known text script, independent of language labels."""
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    expected = sum(
        "a" <= char.casefold() <= "z" or "\u0900" <= char <= "\u097f" for char in letters
    )
    return expected / len(letters)


def text_ink_alignment(
    gray: Image.Image,
    word_boxes: Sequence[tuple[float, float, float, float]],
    width: float,
    height: float,
) -> float:
    """Fraction of text-layer word boxes with rendered dark pixels nearby."""
    if not word_boxes:
        return 1.0
    image = gray.convert("L")
    pixels = image.load()
    assert pixels is not None
    occupied = 0
    for x0, y0, x1, y1 in word_boxes:
        left = max(0, int(x0 * image.width / width))
        right = min(image.width, max(left + 1, int(x1 * image.width / width)))
        top = max(0, int(y0 * image.height / height))
        bottom = min(image.height, max(top + 1, int(y1 * image.height / height)))
        samples = [
            cast(int, pixels[x, y]) for y in range(top, bottom, 2) for x in range(left, right, 2)
        ]
        occupied += bool(samples and sum(value < 170 for value in samples) / len(samples) > 0.012)
    return occupied / len(word_boxes)


def uncovered_ink_ratio(
    gray: Image.Image,
    word_boxes: Sequence[tuple[float, float, float, float]],
    image_rectangles: Sequence[tuple[float, float, float, float]],
    width: float,
    height: float,
) -> float:
    """Share of image-region ink outside padded text-layer word boxes."""
    if not image_rectangles:
        return 0.0
    image = gray.convert("L")
    dark = image.point(lambda value: 255 if value < 210 else 0)
    covered = Image.new("L", image.size, 0)
    image_regions = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(covered)
    image_draw = ImageDraw.Draw(image_regions)
    scale_x, scale_y = image.width / width, image.height / height
    for x0, y0, x1, y1 in image_rectangles:
        image_draw.rectangle(
            (int(x0 * scale_x), int(y0 * scale_y), int(x1 * scale_x), int(y1 * scale_y)),
            fill=255,
        )
    for x0, y0, x1, y1 in word_boxes:
        left = max(0, int(x0 * scale_x) - 1)
        top = max(0, int(y0 * scale_y) - 1)
        right = min(image.width - 1, int(x1 * scale_x) + 1)
        bottom = min(image.height - 1, int(y1 * scale_y) + 1)
        draw.rectangle((left, top, right, bottom), fill=255)
    image_ink = ImageChops.multiply(dark, image_regions)
    outside = ImageChops.subtract(image_ink, covered)
    total_dark = image.width * image.height - image_ink.histogram()[0]
    outside_dark = image.width * image.height - outside.histogram()[0]
    return outside_dark / total_dark if total_dark else 0.0


def rendered_noise_score(gray: Image.Image) -> float:
    """Generic high-frequency noise estimate, normalized to 0-1."""
    image = gray.convert("L")
    pixels = image.load()
    assert pixels is not None
    values: list[float] = []
    for y in range(1, image.height - 1, 2):
        for x in range(1, image.width - 1, 2):
            center = cast(int, pixels[x, y])
            laplacian = (
                4 * center
                - cast(int, pixels[x - 1, y])
                - cast(int, pixels[x + 1, y])
                - cast(int, pixels[x, y - 1])
                - cast(int, pixels[x, y + 1])
            )
            values.append(float(laplacian))
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return min(1.0, variance / 1000.0)


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
    ink_alignment: float = 1.0,
    uncovered_ink: float = 0.0,
    noise_score: float = 0.0,
    previous_table_score: float = 0.0,
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
        text_ink_alignment=ink_alignment,
        uncovered_ink_ratio=uncovered_ink,
        rendered_noise_score=noise_score,
        previous_page_table_likelihood=previous_table_score,
    )


def _table_observations(page: pymupdf.Page) -> tuple[str, int, int]:
    text = page.get_text("text")
    horizontal = sum(
        item[0] == "l" and abs(item[1].y - item[2].y) < 2
        for drawing in page.get_drawings()
        for item in drawing["items"]
    )
    buckets: dict[int, int] = {}
    for word in page.get_text("words"):
        column = round(float(word[0]) / 25)
        buckets[column] = buckets.get(column, 0) + 1
    return text, horizontal, sum(count >= 3 for count in buckets.values())


def inspect_page(pdf: Path, page_number: int) -> PageFeatures:
    """Collect observations; feature calculations remain independently testable."""
    with pymupdf.open(pdf) as document:
        page = document[page_number - 1]
        text, horizontal, columns = _table_observations(page)
        blocks = page.get_text("blocks")
        image_rects = [
            (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
            for image in page.get_images(full=True)
            for rect in page.get_image_rects(image[0])
        ]
        words = page.get_text("words")
        skew = 0.0
        ink_alignment = 1.0
        missing_ink = 0.0
        noise_score = 0.0
        if image_rects or words:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(0.3, 0.3), colorspace=pymupdf.csGRAY)
            gray = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            if image_rects:
                skew = estimate_skew(gray)
            ink_alignment = text_ink_alignment(
                gray,
                [(float(w[0]), float(w[1]), float(w[2]), float(w[3])) for w in words],
                page.rect.width,
                page.rect.height,
            )
            missing_ink = uncovered_ink_ratio(
                gray,
                [(float(w[0]), float(w[1]), float(w[2]), float(w[3])) for w in words],
                image_rects,
                page.rect.width,
                page.rect.height,
            )
            noise_score = rendered_noise_score(gray)
        previous_table_score = 0.0
        if page_number > 1:
            previous_text, previous_horizontal, previous_columns = _table_observations(
                document[page_number - 2]
            )
            previous_table_score = table_likelihood(
                previous_text, previous_horizontal, previous_columns
            )
        return from_observations(
            text,
            page.rect.width,
            page.rect.height,
            image_rects,
            horizontal,
            columns,
            len(blocks),
            skew,
            ink_alignment,
            missing_ink,
            noise_score,
            previous_table_score,
        )
