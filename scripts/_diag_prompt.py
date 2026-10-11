import sys
from pathlib import Path
from app.config import get_settings
from app.services import retrieval_service
from app.prompts import rag_prompts
from app.infrastructure.llm.hf_client import get_llm
from app.services import chat_service

out = []
def p(*a):
    out.append(" ".join(str(x) for x in a))

qs = [
    "What chunk size and overlap does this project use?",
    "What is the maximum upload size for this knowledge base?",
    "Which embedding model does this project use?",
]
q = sys.argv[1] if len(sys.argv) > 1 else qs[0]
settings = get_settings()
llm = get_llm()

sources = retrieval_service.retrieve(q, settings=settings)
p("Q:", q)
p("SOURCES:")
for i, s in enumerate(sources, 1):
    p(f"  {i}. {s.filename} p{s.page} score={s.score}")

context = rag_prompts.build_context(sources, chat_service._full_chunks(sources))
user_prompt = rag_prompts.build_user_prompt(q, context)
p(f"\nSYSTEM len={len(rag_prompts.SYSTEM_PROMPT)} USER len={len(user_prompt)} CONTEXT len={len(context)}")
p("\n--- CONTEXT SENT ---")
p(context)

raw = llm.generate(rag_prompts.SYSTEM_PROMPT, user_prompt)
p("\n--- RAW MODEL OUTPUT ---")
p(raw)
p("\nRAW repr:")
p(repr(raw))

norm = rag_prompts.normalize_citations(raw, sources)
p("\n--- AFTER normalize_citations ---")
p(norm)

Path("scripts/_diag_out.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote scripts/_diag_out.txt")
