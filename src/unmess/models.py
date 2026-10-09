"""Validated, parser-independent document and evaluation records."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BBox(Record):
    page: int = Field(ge=1)
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def valid_extent(self) -> "BBox":
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bbox must have positive width and height")
        return self


class Cell(Record):
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    col_span: int = Field(default=1, ge=1)
    text: str
    bbox: BBox


class Table(Record):
    table_id: str
    page_numbers: list[int] = Field(min_length=1)
    cells: list[Cell] = Field(min_length=1)
    has_merged_cells: bool = False
    spans_pages: bool = False

    @model_validator(mode="after")
    def consistent_pages(self) -> "Table":
        pages = set(self.page_numbers)
        if any(page < 1 for page in pages) or len(pages) != len(self.page_numbers):
            raise ValueError("page numbers must be unique and positive")
        if any(cell.bbox.page not in pages for cell in self.cells):
            raise ValueError("cell bbox page must belong to table")
        if self.spans_pages != (len(pages) > 1):
            raise ValueError("spans_pages must match page count")
        if self.has_merged_cells != any(
            cell.row_span > 1 or cell.col_span > 1 for cell in self.cells
        ):
            raise ValueError("has_merged_cells must match cell spans")
        return self


class Block(Record):
    block_id: str
    kind: Literal["heading", "paragraph", "list", "caption", "table", "figure"]
    text: str
    bbox: BBox
    parent_id: str | None = None


class Page(Record):
    page_number: int = Field(ge=1)
    language: Literal["en", "hi"]
    expected_text: str = ""
    is_ocr_page: bool = False
    blocks: list[Block] = Field(default_factory=list)
    parser_used: str | None = None
    quality_score: float | None = Field(default=None, ge=0, le=1)


class Document(Record):
    document_id: str
    source_file: str
    pages: list[Page] = Field(min_length=1)
    tables: list[Table] = Field(default_factory=list)
    content_hash: str | None = None


class Chunk(Record):
    id: str
    doc_id: str
    text: str
    page_numbers: list[int] = Field(min_length=1)
    bboxes: list[BBox] = Field(default_factory=list)
    section_path: list[str] = Field(default_factory=list)
    parser_used: str
    quality_score: float = Field(ge=0, le=1)
    content_hash: str
    context: str | None = None

    @model_validator(mode="after")
    def valid_provenance(self) -> "Chunk":
        if any(page < 1 for page in self.page_numbers):
            raise ValueError("chunk page numbers must be positive")
        if any(box.page not in self.page_numbers for box in self.bboxes):
            raise ValueError("chunk bbox page must belong to chunk")
        return self


class QualityReport(Record):
    document_id: str
    page_number: int = Field(ge=1)
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    flagged_for_review: bool = False


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Job(Record):
    id: str
    document_id: str | None = None
    status: JobStatus = JobStatus.queued
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class Degradation(Record):
    rotation_deg: float
    noise_level: float = Field(ge=0, le=1)
    dpi: int = Field(gt=0)
    blur: float = Field(ge=0)


class Answer(Record):
    id: str
    question: str
    answer: str
    answer_type: Literal["text", "number", "date", "currency"]
    answer_aliases: list[str] = Field(default_factory=list)
    language: Literal["en", "hi"]
    answering_pages: list[int] = Field(min_length=1)
    answer_bboxes: list[BBox] = Field(default_factory=list)


class GroundTruth(Document):
    schema_version: Literal["1"] = "1"
    category: Literal[
        "clean", "scan", "receipt", "gst_invoice", "merged_table", "spanning_table", "bilingual"
    ]
    split: Literal["dev", "test"]
    seed: int
    questions: list[Answer] = Field(min_length=3, max_length=5)
    degradation: Degradation | None = None

    @model_validator(mode="after")
    def consistent_ground_truth(self) -> "GroundTruth":
        pages = {page.page_number for page in self.pages}
        if pages != set(range(1, len(self.pages) + 1)):
            raise ValueError("pages must be one-based and contiguous")
        if self.category == "scan" and self.degradation is None:
            raise ValueError("scans require degradation parameters")
        if any(set(q.answering_pages) - pages for q in self.questions):
            raise ValueError("answering page outside document")
        if any(
            box.page not in q.answering_pages for q in self.questions for box in q.answer_bboxes
        ):
            raise ValueError("answer bbox outside answering pages")
        return self
