"""Local Ollama vision fallback with a strict response and disk cache."""

import base64
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Protocol

import httpx
import pymupdf
from pydantic import BaseModel, ConfigDict, ValidationError

from unmess.config import Settings
from unmess.models import BBox, Block, Cell, Table
from unmess.parsing.base import ParsedPage

PROMPT_VERSION = "phase2b-v2"
PROMPT = (
    "Transcribe every visible word on this document page. Preserve reading order and use "
    "Markdown table syntax for tables. Return ONLY a JSON object with one key, markdown, "
    "whose value is the complete transcription. Do not add commentary or code fences."
)


def markdown_tables(markdown: str, page_number: int) -> list[Table]:
    """Convert ordinary pipe-table Markdown into parser-independent table grids."""
    lines = markdown.splitlines()
    tables: list[Table] = []
    index = 0
    while index + 1 < len(lines):
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        if not (header.startswith("|") and header.endswith("|")):
            index += 1
            continue
        separator_cells = [cell.strip() for cell in separator.strip("|").split("|")]
        if not separator_cells or not all(
            cell and set(cell.replace(":", "")) <= {"-"} for cell in separator_cells
        ):
            index += 1
            continue
        rows = [[cell.strip() for cell in header.strip("|").split("|")]]
        index += 2
        while index < len(lines):
            candidate = lines[index].strip()
            if not (candidate.startswith("|") and candidate.endswith("|")):
                break
            rows.append([cell.strip() for cell in candidate.strip("|").split("|")])
            index += 1
        width = len(rows[0])
        if width == len(separator_cells) and all(len(row) == width for row in rows):
            whole_page = BBox(page=page_number, x0=0, y0=0, x1=1, y1=1)
            cells = [
                Cell(row=row, col=col, text=value, bbox=whole_page)
                for row, values in enumerate(rows)
                for col, value in enumerate(values)
                if value
            ]
            if cells:
                table_index = len(tables)
                tables.append(
                    Table(
                        table_id=("line-items" if table_index == 0 else f"table-{table_index}"),
                        page_numbers=[page_number],
                        cells=cells,
                    )
                )
        continue
    return tables


class VisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown: str


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
                    "format": VisionResponse.model_json_schema(),
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

    def __init__(
        self,
        settings: Settings,
        client: VisionClient | None = None,
        *,
        allow_model_calls: bool = True,
    ) -> None:
        self.settings = settings
        self.client = client or OllamaVisionClient(str(settings.ollama_url))
        self.allow_model_calls = allow_model_calls

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
            cache_hit = self.settings.vision_cache_reads and cache_path.is_file()
            if cache_hit:
                raw = cache_path.read_text(encoding="utf-8")
            else:
                if not self.allow_model_calls:
                    return ParsedPage.failed(
                        page_number,
                        self.name,
                        "cache miss: VLM baseline model calls disabled",
                        perf_counter() - start,
                    )
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
                    except Exception as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")
                else:
                    return ParsedPage.failed(
                        page_number, self.name, "; ".join(errors), perf_counter() - start
                    )
            parsed = VisionResponse.model_validate_json(raw)
            if not parsed.markdown.strip():
                raise ValueError("empty markdown in cached vision response")
            whole_page = BBox(page=page_number, x0=0, y0=0, x1=1, y1=1)
            block = Block(
                block_id=f"{page_number}:vision-transcription",
                kind="paragraph",
                text=parsed.markdown,
                bbox=whole_page,
            )
            return ParsedPage(
                page_number=page_number,
                parser_name=self.name,
                text=parsed.markdown,
                blocks=[block],
                tables=markdown_tables(parsed.markdown, page_number),
                bboxes=[whole_page],
                parse_time_s=perf_counter() - start,
                cache_hit=cache_hit,
            )
        except (OSError, ValueError, ValidationError, pymupdf.FileDataError) as exc:
            return ParsedPage.failed(
                page_number, self.name, f"{type(exc).__name__}: {exc}", perf_counter() - start
            )
