from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from langchain_core.documents import Document as LC_Document

@runtime_checkable
class Loader(Protocol):
    def supports(self, path: Path) -> bool:
        ...

    def load(self, path: Path) -> list[LC_Document]:
        ...

def get_loader(path: Path) -> Loader:
    from app.infrastructure.loaders.pdf_loader import PdfLoader
    from app.infrastructure.loaders.text_loader import TextLoader

    for loader in (PdfLoader(), TextLoader()):
        if loader.supports(path):
            return loader

    raise ValueError(f"No loader available for file type: {path.suffix!r}")
