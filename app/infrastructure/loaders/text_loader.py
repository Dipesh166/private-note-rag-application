from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document as LC_Document

_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")

class TextLoader:
    SUFFIXES = {".md", ".txt"}

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.SUFFIXES

    def load(self, path: Path) -> list[LC_Document]:
        text = self._read(path)
        source = path.name

        return [
            LC_Document(
                page_content=text,
                metadata={
                    "source": source,
                    "page": 1,
                    "ext": path.suffix.lower(),
                },
            )
        ]

    @staticmethod
    def _read(path: Path) -> str:
        last_error: UnicodeDecodeError | None = None
        for encoding in _ENCODINGS:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc

        raise last_error
