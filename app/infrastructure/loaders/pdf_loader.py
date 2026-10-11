from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document as LC_Document

class PdfLoader:
    PDF_SUFFIX = ".pdf"

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == self.PDF_SUFFIX

    def load(self, path: Path) -> list[LC_Document]:
        docs = PyPDFLoader(str(path), mode="page").load()

        source = path.name
        for doc in docs:
            doc.metadata.setdefault("source", source)
            doc.metadata["source"] = source

            doc.metadata["page"] = int(doc.metadata.get("page", 0)) + 1
            doc.metadata["ext"] = self.PDF_SUFFIX

        return docs
