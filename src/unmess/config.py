"""Environment-backed configuration for all pipeline services and thresholds."""

from pathlib import Path

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UNMESS_", env_file=".env", extra="ignore")

    env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: HttpUrl = HttpUrl("http://localhost:6333")
    qdrant_collection: str = "unmess_chunks"
    ollama_url: HttpUrl = HttpUrl("http://localhost:11434")
    text_model: str = "qwen3"
    vision_model: str = "qwen2.5vl"
    docling_artifacts_path: Path = Path.home() / ".cache/docling/models"
    embed_model: str = "bge-m3"
    rerank_enabled: bool = False
    parser_text_density_threshold: float = Field(default=0.12, ge=0, le=1)
    parser_image_coverage_threshold: float = Field(default=0.70, ge=0, le=1)
    parser_table_likelihood_threshold: float = Field(default=0.55, ge=0, le=1)
    parser_scan_likelihood_threshold: float = Field(default=0.60, ge=0, le=1)
    parser_complex_layout_threshold: float = Field(default=0.90, ge=0, le=1)
    parser_garbled_ratio_threshold: float = Field(default=0.10, ge=0, le=1)
    parser_max_skew_degrees: float = Field(default=3.0, ge=0, le=90)
    quality_review_threshold: float = Field(default=0.70, ge=0, le=1)
    vision_timeout_s: float = Field(default=120.0, gt=0, le=300)
    vision_retries: int = Field(default=1, ge=0, le=5)
    vision_raster_dpi: int = Field(default=110, ge=50, le=300)
    vision_cache_dir: Path = Path(".cache/unmess/vlm")
    chunk_target_tokens: int = Field(default=600, gt=0)
    chunk_overlap_tokens: int = Field(default=80, ge=0)

    @model_validator(mode="after")
    def valid_chunk_window(self) -> "Settings":
        if self.chunk_overlap_tokens >= self.chunk_target_tokens:
            raise ValueError("chunk overlap must be smaller than target")
        return self

    @field_validator("redis_url")
    @classmethod
    def valid_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            raise ValueError("redis_url must use redis:// or rediss://")
        return value

    @field_validator("text_model", "vision_model", "embed_model", "qdrant_collection")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("unsupported log level")
        return value

    @field_validator("ollama_url")
    @classmethod
    def local_ollama_only(cls, value: HttpUrl) -> HttpUrl:
        if value.host not in {"localhost", "127.0.0.1", "::1", "host.docker.internal", "ollama"}:
            raise ValueError("Ollama must be on the local host or Compose network")
        return value
