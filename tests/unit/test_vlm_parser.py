import json
from pathlib import Path

import pytest

from unmess.config import Settings
from unmess.parsing.vlm_parser import VLMParser


class FakeClient:
    def __init__(self, result: str, model: str = "mock-vision") -> None:
        self.result = result
        self.model = model
        self.calls = 0

    def generate(self, model: str, prompt: str, image_b64: str, timeout_s: float) -> str:
        self.calls += 1
        assert model == self.model
        assert image_b64
        return self.result


def test_vlm_cache_uses_model_and_prompt_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FakeClient(json.dumps({"markdown": "Read text"}))
    settings = Settings(vision_model="mock-vision", vision_cache_dir=tmp_path, vision_retries=0)
    parser = VLMParser(settings, client)
    monkeypatch.setattr(parser, "_image", lambda _pdf, _page: b"fake-png")
    first = parser.parse_page(Path("fake.pdf"), 1)
    second = parser.parse_page(Path("fake.pdf"), 1)
    assert first.success and second.success
    assert not first.cache_hit and second.cache_hit
    assert first.bboxes[0].x1 == 1
    assert client.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 1
    other_client = FakeClient(client.result, model="second-model")
    other = VLMParser(
        Settings(vision_model="second-model", vision_cache_dir=tmp_path, vision_retries=0),
        other_client,
    )
    monkeypatch.setattr(other, "_image", lambda _pdf, _page: b"fake-png")
    assert other.parse_page(Path("fake.pdf"), 1).success
    assert other_client.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_vlm_invalid_output_is_failed_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient("not JSON")
    parser = VLMParser(
        Settings(vision_model="mock-vision", vision_cache_dir=tmp_path, vision_retries=1),
        client,
    )
    monkeypatch.setattr(parser, "_image", lambda _pdf, _page: b"fake-png")
    page = parser.parse_page(Path("fake.pdf"), 1)
    assert not page.success
    assert client.calls == 2
    assert not list(tmp_path.glob("*.json"))
