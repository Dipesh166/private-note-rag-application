from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.infrastructure.llm.hf_client import HFTransformersClient, get_llm
from app.infrastructure.registry.json_registry import DocumentRegistry, get_registry
from app.infrastructure.vectorstore.chroma_store import get_vectorstore

@lru_cache
def settings_dep() -> Settings:
    return get_settings()

@lru_cache
def vectorstore_dep():
    return get_vectorstore()

def registry_dep() -> DocumentRegistry:
    return get_registry()

def llm_dep() -> HFTransformersClient:
    return get_llm()
