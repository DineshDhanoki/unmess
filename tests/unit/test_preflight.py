"""Mocked backend preflight contract; live Ollama stays opt-in."""

from types import SimpleNamespace
from typing import Any

import pytest

from eval.preflight import run_preflight
from unmess.config import Settings


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeHttpClient:
    def __init__(self, *args: Any, pulled: bool = True, **kwargs: Any) -> None:
        self.pulled = pulled

    def __enter__(self) -> "FakeHttpClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        pass

    def get(self, _url: str) -> FakeResponse:
        models = [{"name": "mock:latest"}] if self.pulled else []
        return FakeResponse({"models": models})

    def post(self, _url: str, json: dict[str, Any]) -> FakeResponse:
        assert json["model"] == "mock"
        return FakeResponse({"response": "OK"})


class FakeParser:
    def __init__(self, *_args: Any) -> None:
        pass

    def parse_page(self, *_args: Any) -> SimpleNamespace:
        return SimpleNamespace(success=True, text="dev text")


def test_preflight_checks_all_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eval.preflight.importlib.import_module", lambda _name: object())
    monkeypatch.setattr("eval.preflight.PyMuPDFParser", FakeParser)
    monkeypatch.setattr("eval.preflight.DoclingParser", FakeParser)
    monkeypatch.setattr("eval.preflight.httpx.Client", FakeHttpClient)
    result = run_preflight(Settings(vision_model="mock"))
    assert result["pymupdf_parse"] == "ok"
    assert result["docling_parse"] == "ok"
    assert result["vision_response"] == "OK"


def test_preflight_rejects_missing_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eval.preflight.importlib.import_module", lambda _name: object())
    monkeypatch.setattr("eval.preflight.PyMuPDFParser", FakeParser)
    monkeypatch.setattr("eval.preflight.DoclingParser", FakeParser)
    monkeypatch.setattr(
        "eval.preflight.httpx.Client", lambda **_kwargs: FakeHttpClient(pulled=False)
    )
    with pytest.raises(RuntimeError, match="not pulled"):
        run_preflight(Settings(vision_model="mock"))
