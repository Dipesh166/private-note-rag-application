from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

class ErrorOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"detail": "Unsupported file type '.exe'", "code": "unsupported_type"}
    })

    detail: str
    code: str = Field(description="Machine-readable error code")

class HealthOut(BaseModel):
    status: str = "ok"
    llm: bool = Field(description="Whether the local generation model is loadable")
    llm_ready: bool = Field(
        default=False,
        description="Whether the generation model is loaded in memory and ready",
    )
    llm_device: str = Field(description="cpu | cuda — where generation runs")
    embedding_model: str
    indexed_docs: int
    total_chunks: int

class OkOut(BaseModel):
    detail: str
    removed: int = 0
