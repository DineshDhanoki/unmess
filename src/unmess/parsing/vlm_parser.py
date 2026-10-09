"""Local Ollama vision fallback with a strict response and disk cache."""

import base64
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Protocol

import httpx
import pymupdf
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from unmess.config import Settings
from unmess.models import Block, Table
from unmess.parsing.base import ParsedPage

PROMPT_VERSION = "phase2-v1"
PROMPT = (
    "Transcribe this page. Return ONLY a JSON object with keys markdown, blocks, tables, "
    "reported_confidence. markdown is the complete page text in Markdown. blocks is a list "
    "of objects with block_id, kind, text, bbox; bbox has page, x0, y0, x1, y1 with "
    "top-left normalized coordinates in [0,1]. tables is a list of objects with table_id, "
    "page_numbers, cells, has_merged_cells, spans_pages. Each cell has row, col, row_span, "
    "col_span, text, bbox. Use an empty list where none exist. Do not add prose or code fences."
)


class VisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown: str
    blocks: list[Block]
    tables: list[Table]
    reported_confidence: float | None = Field(default=None, ge=0, le=1)


class VisionClient(Protocol):
    def generate(self, model: str, prompt: str, image_b64: str, timeout_s: float) -> str: ...


class OllamaVisionClient:
    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def generate(self, model: str, prompt: str, image_b64: str, timeout_s: float) -> str:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(
                f"{self.url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "format": "json",
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            result = payload.get("response")
            if not isinstance(result, str):
                raise ValueError("Ollama response missing response string")
            return result


class VLMParser:
    name = "vlm"

    def __init__(self, settings: Settings, client: VisionClient | None = None) -> None:
        self.settings = settings
        self.client = client or OllamaVisionClient(str(settings.ollama_url))

    def _image(self, pdf: Path, page_number: int) -> bytes:
        with pymupdf.open(pdf) as document:
            image: bytes = (
                document[page_number - 1]
                .get_pixmap(dpi=self.settings.vision_raster_dpi, alpha=False)
                .tobytes("png")
            )
            return image

    def _cache_path(self, image: bytes) -> Path:
        page_hash = hashlib.sha256(image).hexdigest()
        key = hashlib.sha256(
            f"{page_hash}|{self.settings.vision_model}|{PROMPT_VERSION}".encode()
        ).hexdigest()
        return self.settings.vision_cache_dir / f"{key}.json"

    def parse_page(self, pdf: Path, page_number: int) -> ParsedPage:
        start = perf_counter()
        try:
            image = self._image(pdf, page_number)
            cache_path = self._cache_path(image)
            if cache_path.is_file():
                raw = cache_path.read_text(encoding="utf-8")
            else:
                errors: list[str] = []
                for _attempt in range(self.settings.vision_retries + 1):
                    try:
                        raw = self.client.generate(
                            self.settings.vision_model,
                            PROMPT,
                            base64.b64encode(image).decode("ascii"),
                            self.settings.vision_timeout_s,
                        )
                        parsed = VisionResponse.model_validate_json(raw)
                        if not parsed.markdown.strip():
                            raise ValueError("empty markdown in vision response")
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_text(parsed.model_dump_json(), encoding="utf-8")
                        break
                    except (httpx.HTTPError, ValueError, ValidationError) as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")
                else:
                    return ParsedPage.failed(
                        page_number, self.name, "; ".join(errors), perf_counter() - start
                    )
            parsed = VisionResponse.model_validate_json(raw)
            if not parsed.markdown.strip():
                raise ValueError("empty markdown in cached vision response")
            if any(block.bbox.page != page_number for block in parsed.blocks):
                raise ValueError("vision block bbox page mismatch")
            if any(page_number not in table.page_numbers for table in parsed.tables):
                raise ValueError("vision table page mismatch")
            return ParsedPage(
                page_number=page_number,
                parser_name=self.name,
                text=parsed.markdown,
                blocks=parsed.blocks,
                tables=parsed.tables,
                bboxes=[block.bbox for block in parsed.blocks],
                parse_time_s=perf_counter() - start,
                reported_confidence=parsed.reported_confidence,
            )
        except (OSError, ValueError, ValidationError, pymupdf.FileDataError) as exc:
            return ParsedPage.failed(
                page_number, self.name, f"{type(exc).__name__}: {exc}", perf_counter() - start
            )
