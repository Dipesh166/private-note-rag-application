from functools import lru_cache
import os
from pathlib import Path

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Private Knowledge Base API"
    api_v1_prefix: str = "/v1"
    debug: bool = False

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    data_dir: Path = BASE_DIR / "data"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    chroma_dir: Path = BASE_DIR / "data" / "chroma"
    registry_file: Path = BASE_DIR / "data" / "registry.json"

    embedding_model: str = "all-MiniLM-L6-v2"

    chunk_size: int = 1000
    chunk_overlap: int = 150

    top_k: int = 6
    fetch_k: int = 20
    lambda_mult: float = 0.25
    min_score: float = 0.2

    llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"

    llm_device: str = "auto"
    llm_max_new_tokens: int = 768
    llm_temperature: float = 0.0
    llm_timeout_s: float = 120.0

    @property
    def resolved_llm_device(self) -> str:
        if self.llm_device != "auto":
            return self.llm_device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    max_upload_mb: int = 20

    allowed_extensions: Annotated[set[str], NoDecode] = {".pdf", ".md", ".txt"}

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    seed_markdown: Path = (
        BASE_DIR / "Private_Knowledge_Base_Local_RAG_Project_Plan (1).md"
    )

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def _split_extensions(cls, value: object) -> object:
        if isinstance(value, str):
            return {v.strip() for v in value.split(",") if v.strip()}
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @field_validator("chroma_dir", "upload_dir", "data_dir")
    @classmethod
    def _ensure_dir(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value

@lru_cache
def get_settings() -> Settings:
    return Settings()
