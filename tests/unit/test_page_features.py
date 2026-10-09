from PIL import Image, ImageDraw

from unmess.parsing.page_features import (
    area_coverage,
    dominant_script,
    estimate_skew,
    from_observations,
    garbled_ratio,
    scan_likelihood,
    table_likelihood,
    text_density,
)


def test_pure_features_identify_scan_table_and_script() -> None:
    assert text_density("abc", 100, 100) == 0.3
    assert area_coverage([(0, 0, 100, 100)], 100, 100) == 1
    assert scan_likelihood(0, 1) == 1
    assert table_likelihood("Item Qty Amount", 4, 3) > 0.55
    assert dominant_script("कुल राशि") == "Devanagari"
    assert dominant_script("Total INR") == "Latin"
    assert garbled_ratio("abc\ufffd") == 0.25
    features = from_observations("", 100, 100, [(0, 0, 100, 100)], 0, 0, 0, 0)
    assert features.scan_likelihood == 1


def test_skew_estimator_uses_image_projection() -> None:
    image = Image.new("L", (200, 100), 255)
    ImageDraw.Draw(image).line((10, 50, 190, 50), fill=0, width=3)
    assert estimate_skew(image) == 0
