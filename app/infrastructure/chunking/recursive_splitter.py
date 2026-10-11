from __future__ import annotations

from langchain_core.documents import Document as LC_Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings

def build_splitter(settings: Settings) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

def chunk_documents(
    docs: list[LC_Document],
    settings: Settings,
    doc_id: str,
) -> list[LC_Document]:
    splitter = build_splitter(settings)
    chunks = splitter.split_documents(docs)

    total = len(chunks)
    for index, chunk in enumerate(chunks):
        meta = chunk.metadata
        meta["doc_id"] = doc_id
        meta["chunk_id"] = f"{doc_id}:{index:04d}"
        meta.setdefault("source", "unknown")
        meta.setdefault("page", 1)

        if not chunk.page_content.strip():
            raise ValueError(
                f"Chunk {index} of {meta['source']} is empty — "
                "document likely failed text extraction."
            )

    assert total == len(chunks)
    return chunks
