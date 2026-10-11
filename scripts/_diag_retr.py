import numpy as np
from app.config import get_settings
from app.infrastructure.vectorstore.chroma_store import get_vectorstore
from app.infrastructure.embeddings.minilm_embedder import get_embeddings
from app.infrastructure.registry.json_registry import get_registry

settings = get_settings()
store = get_vectorstore()
emb = get_embeddings()
print("min_score floor =", settings.min_score)

reg = get_registry()
by_id = {d.doc_id: d.filename for d in reg.list()}
print("indexed docs:", by_id)

for q in ["What is the maximum upload size for this knowledge base?",
          "What embedding model does this project use?",
          "What chunk size does this project use?"]:
    print("\n" + "=" * 70)
    print("Q:", q)
    qv = np.asarray(emb.embed_query(q), dtype=np.float32)
    results = store.similarity_search_by_vector_with_relevance_scores(qv, k=20)
    ids = [d.metadata["chunk_id"] for d, _ in results]
    stored = store._collection.get(ids=ids, include=["embeddings"])
    vm = {c: np.asarray(v, dtype=np.float32)
          for c, v in zip(stored["ids"], stored["embeddings"])}
    rel = np.stack([vm[c] for c in ids]) @ qv
    order = np.argsort(-rel)
    for rank, i in enumerate(order, 1):
        doc = results[i][0]
        fn = by_id.get(doc.metadata.get("doc_id", ""), doc.metadata.get("source", "?"))
        print(f"  {rank:2d}. cos={rel[i]:.4f} p{doc.metadata.get('page')} "
              f"[{fn}] {doc.page_content[:70].replace(chr(10), ' ')}")
    print(f"  above floor {settings.min_score}: {(rel >= settings.min_score).sum()}/20")
