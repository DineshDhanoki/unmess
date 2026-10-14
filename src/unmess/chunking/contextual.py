"""Optional local one-line chunk context with content-addressed caching."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import httpx

from unmess.chunking.schema import ChunkRecord


@dataclass(frozen=True)
class ContextConfig:
    enabled: bool = False
    model: str = "qwen3"
    ollama_url: str = "http://localhost:11434"
    timeout_s: float = 60.0
    cache_dir: Path = Path(".cache/unmess/context")


DEFAULT_CONTEXT_CONFIG = ContextConfig()


def add_context(chunk: ChunkRecord, config: ContextConfig = DEFAULT_CONTEXT_CONFIG) -> ChunkRecord:
    if not config.enabled:
        return chunk
    cache_path = config.cache_dir / f"{chunk.content_hash}.json"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return replace(chunk, context=str(payload["context"]))
    response = httpx.post(
        f"{config.ollama_url.rstrip('/')}/api/generate",
        json={
            "model": config.model,
            "prompt": (
                "Write one factual line describing this chunk's role in its document. "
                "Do not add facts. Return only that line.\n\n" + chunk.markdown
            ),
            "stream": False,
        },
        timeout=config.timeout_s,
    )
    response.raise_for_status()
    context = str(response.json()["response"]).strip().splitlines()[0]
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"context": context}) + "\n", encoding="utf-8")
    return replace(chunk, context=context)
