from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.constants import (
    QUESTION_MAX_CHARS,
    QUESTION_MIN_CHARS,
    TOP_K_MAX,
    TOP_K_MIN,
)

class ChatRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"question": "What embedding model does this project use?"}
    })

    question: str = Field(
        min_length=QUESTION_MIN_CHARS,
        max_length=QUESTION_MAX_CHARS,
        description="Natural-language question to answer from indexed documents.",
    )
    doc_ids: list[str] | None = Field(
        default=None,
        description="Restrict retrieval to these documents. Omitted = search all.",
    )
    top_k: int | None = Field(
        default=None,
        ge=TOP_K_MIN,
        le=TOP_K_MAX,
        description="How many chunks to retrieve (defaults to TOP_K config).",
    )

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < QUESTION_MIN_CHARS:
            raise ValueError("question must contain more than whitespace")
        return cleaned

    @field_validator("doc_ids")
    @classmethod
    def _drop_empty_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [v.strip() for v in value if v and v.strip()]
        return cleaned or None

class SourceOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "doc_id": "8cba06955379",
            "filename": "sample.pdf",
            "page": 2,
            "chunk_id": "8cba06955379:0001",
            "excerpt": "Page two: Python is a programming language...",
            "score": 0.7817,
        }
    })

    doc_id: str
    filename: str
    page: int
    chunk_id: str
    excerpt: str = Field(description="First 300 chars of the retrieved chunk")
    score: float = Field(description="Cosine similarity to the question (0..1)")

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    retrieval_ms: int = Field(description="Time spent retrieving, excluding generation")
    model: str
