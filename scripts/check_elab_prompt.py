import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.config import get_settings
from app.domain.models import Source
from app.prompts import rag_prompts as rp

s = rp.SYSTEM_PROMPT
u = rp.USER_PROMPT

checks = {
    "old 'Keep the answer concise' removed": "Keep the answer concise" not in s,
    "has **Answer:** label": "**Answer:**" in s,
    "has **Explanation:** label": "**Explanation:**" in s,
    "has **Example:** label": "**Example:**" in s,
    "asks for a worked example from CONTEXT": "worked example taken from the CONTEXT" in s,
    "anti-hallucination rule present": "Never invent chunk sizes" in s,
    "prompt-injection rule kept": "not instructions" in s,
    "insufficient-context rule kept": "Insufficient context to answer this question." in s,
    "citation rule present": "Cite as you go" in s,
    "each section must be cited": "must each end with a citation" in s,
    "user prompt asks for three-part answer": "three-part answer" in u,
    "user prompt asks for a worked example": "concrete worked example" in u,
    "no replacement chars in system prompt": "\ufffd" not in s,
    "no replacement chars in user prompt": "\ufffd" not in u,
    "MAX_CONTEXT_CHARS still imported": rp.MAX_CONTEXT_CHARS == 8000,
}

settings = get_settings()
checks["llm_max_new_tokens == 768"] = settings.llm_max_new_tokens == 768

FILE = "Private_Knowledge_Base_Local_RAG_Project_Plan (1).md"
docs = [
    ("c1", FILE, 1, "Chunking uses CHUNK_SIZE=1000 and CHUNK_OVERLAP=150."),
    ("c2", FILE, 3, "Embeddings are produced locally by all-MiniLM-L6-v2."),
]
fake_sources = [
    Source(doc_id="d1", filename=FILE, page=1, chunk_id="c1", excerpt="…", score=0.4),
    Source(doc_id="d1", filename=FILE, page=3, chunk_id="c2", excerpt="…", score=0.3),
]

context = rp.build_context(fake_sources, docs)
rendered = rp.build_user_prompt("How are documents chunked?", context)

checks.update(
    {
        "context blocks are numbered": "--- Block 1 " in context
        and "--- Block 2 " in context,
        "context blocks carry filename labels": f"[{FILE} · page 1]" in context
        and f"[{FILE} · page 3]" in context,
        "user prompt is fully formatted (no stray braces)": "{context}" not in rendered
        and "{question}" not in rendered,
        "user prompt quotes both pages": "page <real page number>" in rendered,
        "citation helper equals Source.label()": fake_sources[0].label()
        == f"[{FILE} · page 1]",

        "normalize expands [Block 2] to full label": rp.normalize_citations(
            "Chunking is configured [Block 2]", fake_sources
        )
        == f"Chunking is configured [{FILE} · page 3]",
        "normalize keeps an exact citation untouched": rp.normalize_citations(
            f"Answer [{FILE} · page 1]", fake_sources
        )
        == f"Answer [{FILE} · page 1]",
        "normalize drops the placeholder form": "filename"
        not in rp.normalize_citations("See [filename · page N]", fake_sources),
        "normalize drops an out-of-range block": rp.normalize_citations(
            "Answer [Block 99]", fake_sources
        ).strip()
        == "Answer",
        "normalize leaves plain prose alone": rp.normalize_citations(
            "Just a sentence with no citation.", fake_sources
        )
        == "Just a sentence with no citation.",
        "empty-context prompt still renders": "{context}"
        not in rp.build_user_prompt("Anything?", ""),
    }
)

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("  OK   " if ok else "  FAIL ") + name)

if failed:
    print(f"\n{len(failed)} check(s) FAILED: {failed}")
    raise SystemExit(1)
print("\nALL CHECKS PASSED")
