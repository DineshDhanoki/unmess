import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from unmess.config import Settings
from unmess.parsing.base import ParsedPage
from unmess.parsing.page_features import PageFeatures, inspect_page
from unmess.parsing.router import PageRouter
from unmess.quality.gates import review_gate
from unmess.quality.scorer import score_page


def features(
    text: str = "A digital page with enough embedded text for extraction.",
    image: float = 0,
    table: float = 0,
) -> PageFeatures:
    return PageFeatures(
        embedded_text=text,
        embedded_text_density=0.25 if text else 0,
        image_coverage=image,
        scan_likelihood=image,
        table_likelihood=table,
        skew_degrees=0,
        garbled_character_ratio=0,
        dominant_script="Latin",
        layout_complexity=table,
    )


class StubParser:
    def __init__(self, name: str, result: str, success: bool = True) -> None:
        self.name, self.result, self.success = name, result, success
        self.calls = 0

    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage:
        self.calls += 1
        if not self.success:
            return ParsedPage.failed(page_number, self.name, "unavailable")
        return ParsedPage(page_number=page_number, parser_name=self.name, text=self.result)


def test_clean_page_uses_fast_path() -> None:
    text = "A digital page with enough embedded text for extraction."
    fast, heavy, vision = (
        StubParser("pymupdf", text),
        StubParser("docling", text),
        StubParser("vlm", text),
    )
    router = PageRouter(Settings(), fast, heavy, vision, lambda _pdf, _page: features(text))
    page = router.parse_page(Path("sample.pdf"), 1)
    assert page.parser_name == "pymupdf"
    assert page.route_reason == "clean_digital_text"
    assert [fast.calls, heavy.calls, vision.calls] == [1, 0, 0]


def test_table_routes_docling_and_escalates_once_on_failure() -> None:
    heavy = StubParser("docling", "", success=False)
    vision = StubParser("vlm", "Recovered text from the page")
    router = PageRouter(
        Settings(),
        StubParser("pymupdf", ""),
        heavy,
        vision,
        lambda _pdf, _page: features(table=0.8),
    )
    page = router.parse_page(Path("sample.pdf"), 1)
    assert [attempt.parser for attempt in page.attempts] == ["docling", "vlm"]
    assert heavy.calls == vision.calls == 1
    assert "escalated" in page.route_reason


def test_failed_vision_is_reviewed_and_scores_zero() -> None:
    scan = features(text="", image=1)
    vision = StubParser("vlm", "", success=False)
    router = PageRouter(
        Settings(),
        StubParser("pymupdf", ""),
        StubParser("docling", ""),
        vision,
        lambda _pdf, _page: scan,
    )
    page = router.parse_page(Path("scan.pdf"), 1)
    assert page.quality_score == 0
    assert page.review_reasons == ["parser_failed", "below_quality_threshold", "empty_text"]
    assert len(page.attempts) == 1
    assert score_page(page, scan, Settings()).score == 0
    assert review_gate("scan", page, scan, Settings()).flagged_for_review


def test_text_density_threshold_changes_route() -> None:
    text = "A digital page with enough embedded text for extraction."
    fast = StubParser("pymupdf", text)
    vision = StubParser("vlm", text)
    router = PageRouter(
        Settings(parser_text_density_threshold=0.26),
        fast,
        StubParser("docling", text),
        vision,
        lambda _pdf, _page: features(text),
    )
    assert router.parse_page(Path("sample.pdf"), 1).parser_name == "vlm"
    assert fast.calls == 0 and vision.calls == 1


def test_dense_but_ink_misaligned_text_escalates() -> None:
    bad = "qxzvbfkpm " * 25
    observations = features(bad)
    observations = PageFeatures(**{**observations.__dict__, "text_ink_alignment": 0.0})
    fast = StubParser("pymupdf", bad)
    vision = StubParser("vlm", "Readable visual content from the rendered page")
    router = PageRouter(
        Settings(), fast, StubParser("docling", bad), vision, lambda _pdf, _page: observations
    )
    parsed = router.parse_page(Path("broken.pdf"), 1)
    assert [attempt.parser for attempt in parsed.attempts] == ["pymupdf", "vlm"]
    assert parsed.attempts[0].quality_score < Settings().quality_review_threshold


def _png_bytes(image: Image.Image) -> bytes:
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_uncovered_english_raster_line_and_stamp_route_to_vision(tmp_path: Path) -> None:
    pdf = tmp_path / "mixed-visible-content.pdf"
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    for index, line in enumerate(
        (
            "Synthetic service record",
            "Document code: FIXTURE-001",
            "Seller: Example Test Vendor",
            "Issue date: 2026-10-12",
            "Total: INR 12,345",
        )
    ):
        page.insert_text((60, 80 + index * 30), line, fontsize=12)
    raster_line = Image.new("RGB", (420, 54), "white")
    ImageDraw.Draw(raster_line).text((8, 15), "Approved after visual inspection", fill="black")
    page.insert_image(pymupdf.Rect(60, 260, 480, 314), stream=_png_bytes(raster_line))
    stamp = Image.new("RGB", (110, 70), "white")
    stamp_draw = ImageDraw.Draw(stamp)
    stamp_draw.ellipse((8, 5, 102, 64), outline="navy", width=4)
    stamp_draw.line((18, 48, 44, 25, 70, 51, 94, 18), fill="navy", width=3)
    page.insert_image(pymupdf.Rect(420, 350, 530, 420), stream=_png_bytes(stamp))
    document.set_metadata({"producer": "Unmess test fixture", "creationDate": "D:20261012000000Z"})
    document.save(pdf, garbage=4, deflate=True, no_new_id=True)
    document.close()

    observed = inspect_page(pdf, 1)
    assert observed.dominant_script == "Latin"
    assert observed.uncovered_ink_ratio >= Settings().parser_uncovered_ink_threshold
    fast = StubParser("pymupdf", observed.embedded_text)
    vision = StubParser("vlm", observed.embedded_text + " Approved after visual inspection")
    router = PageRouter(Settings(), fast, StubParser("docling", observed.embedded_text), vision)
    parsed = router.parse_page(pdf, 1)
    assert parsed.parser_name == "vlm"
    assert parsed.route_reason == "rendered_ink_not_covered_by_text_layer"
    assert fast.calls == 0 and vision.calls == 1
