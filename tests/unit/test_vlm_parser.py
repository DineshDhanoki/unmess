import json
from pathlib import Path

import pytest

from unmess.config import Settings
from unmess.parsing.vlm_parser import OllamaVisionClient, VLMParser, markdown_tables


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


class FailingClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, model: str, prompt: str, image_b64: str, timeout_s: float) -> str:
        self.calls += 1
        raise RuntimeError("temporary local model failure")


def test_default_ollama_client_receives_configured_generation_options() -> None:
    settings = Settings(
        vision_temperature=0.2,
        vision_repeat_penalty=1.2,
        vision_repeat_last_n=32,
        vision_num_predict=1024,
    )
    parser = VLMParser(settings)

    assert isinstance(parser.client, OllamaVisionClient)
    assert parser.client.options == {
        "temperature": 0.2,
        "repeat_penalty": 1.2,
        "repeat_last_n": 32,
        "num_predict": 1024,
    }


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


def test_vlm_cache_reads_can_be_disabled_for_cold_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FakeClient(json.dumps({"markdown": "Read text"}))
    parser = VLMParser(
        Settings(
            vision_model="mock-vision",
            vision_cache_dir=tmp_path,
            vision_cache_reads=False,
            vision_retries=0,
        ),
        client,
    )
    monkeypatch.setattr(parser, "_image", lambda _pdf, _page: b"same-page")

    first = parser.parse_page(Path("fake.pdf"), 1)
    second = parser.parse_page(Path("fake.pdf"), 1)

    assert not first.cache_hit and not second.cache_hit
    assert client.calls == 2


def test_vlm_runtime_failure_retries_then_returns_failed_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FailingClient()
    parser = VLMParser(
        Settings(vision_model="mock-vision", vision_cache_dir=tmp_path, vision_retries=2),
        client,
    )
    monkeypatch.setattr(parser, "_image", lambda _pdf, _page: b"fake-png")
    page = parser.parse_page(Path("fake.pdf"), 1)
    assert not page.success
    assert client.calls == 3
    assert "temporary local model failure" in (page.error or "")


def test_markdown_table_contract_emits_table_model() -> None:
    tables = markdown_tables(
        "Text\n\n| Item | Qty | Amount |\n|---|---:|---:|\n| Tea | 2 | 250 |",
        3,
    )
    assert len(tables) == 1
    assert tables[0].table_id == "line-items"
    assert [(cell.row, cell.col, cell.text) for cell in tables[0].cells] == [
        (0, 0, "Item"),
        (0, 1, "Qty"),
        (0, 2, "Amount"),
        (1, 0, "Tea"),
        (1, 1, "2"),
        (1, 2, "250"),
    ]
    assert all(cell.bbox.page == 3 for cell in tables[0].cells)
