"""Verify that every Phase 2 parsing backend can execute before locked evaluation."""

import importlib
from pathlib import Path
from typing import Any

import httpx

from unmess.config import Settings
from unmess.parsing.docling_parser import DoclingParser
from unmess.parsing.pymupdf_parser import PyMuPDFParser

ROOT = Path(__file__).resolve().parents[1]
DOCLING_SMOKE_PDF = ROOT / "eval/datasets/pdf/synthetic-gst_invoice-00.pdf"
PYMUPDF_SMOKE_PDF = ROOT / "eval/datasets/pdf/synthetic-clean-00.pdf"


def run_preflight(settings: Settings | None = None) -> dict[str, str]:
    """Exercise Docling on a dev fixture and ask the pulled local vision model to reply."""
    config = settings or Settings()
    results: dict[str, str] = {}
    try:
        page = PyMuPDFParser().parse_page(PYMUPDF_SMOKE_PDF, 1)
        if not page.success or not page.text.strip():
            raise RuntimeError("PyMuPDF returned no text from the dev clean PDF")
        results["pymupdf_parse"] = "ok"
    except Exception as exc:
        raise RuntimeError(f"PyMuPDF unavailable: {type(exc).__name__}: {exc}") from exc
    try:
        importlib.import_module("docling.document_converter")
        results["docling_import"] = "ok"
        page = DoclingParser(config.docling_artifacts_path).parse_page(DOCLING_SMOKE_PDF, 1)
        if not page.success or not page.text.strip():
            raise RuntimeError("Docling returned no text from the dev invoice")
        results["docling_parse"] = "ok"
    except Exception as exc:
        raise RuntimeError(f"Docling unavailable: {type(exc).__name__}: {exc}") from exc

    url = str(config.ollama_url).rstrip("/")
    try:
        with httpx.Client(timeout=120.0) as client:
            tags = client.get(f"{url}/api/tags")
            tags.raise_for_status()
            payload: Any = tags.json()
            names = {item["name"] for item in payload["models"]}
            wanted = config.vision_model
            if wanted not in names and f"{wanted}:latest" not in names:
                raise RuntimeError(f"VISION_MODEL {wanted!r} is not pulled")
            results["ollama_reachable"] = url
            results["vision_model"] = wanted
            answer = client.post(
                f"{url}/api/generate",
                json={
                    "model": wanted,
                    "prompt": "Reply with exactly OK.",
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": 8},
                },
            )
            answer.raise_for_status()
            response = answer.json().get("response", "")
            if not isinstance(response, str) or not response.strip():
                raise RuntimeError("vision model returned an empty trivial response")
            results["vision_response"] = response.strip()
    except Exception as exc:
        raise RuntimeError(f"Ollama preflight failed: {type(exc).__name__}: {exc}") from exc
    return results


def main() -> None:
    print("Phase 2 backend preflight")
    try:
        for name, value in run_preflight().items():
            print(f"{name}: {value}")
    except RuntimeError as exc:
        print(f"FAILED: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
