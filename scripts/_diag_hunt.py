import re
from app.config import get_settings
from app.services import retrieval_service, chat_service
from app.prompts import rag_prompts
from app.infrastructure.llm.hf_client import get_llm

settings = get_settings()
llm = get_llm()

QS = [
    "What is the maximum upload size for this knowledge base?",
    "What embedding model does this project use?",
    "Who won the 1998 football world cup?",
    "Explain chunking in extreme detail with many examples and background and history and everything.",
    "!!!!",
    "asdfghjkl",
    "Write a very long detailed answer about everything you know.",
    "What is the meaning of life?",
]

def degenerate(s: str) -> bool:
    if len(s) > 60 and len(set(s)) < 6:
        return True
    if re.search(r"(.)\1{19,}", s):
        return True
    return False

lines = []
for q in QS:
    try:
        res = chat_service.answer(q, settings=None) if False else chat_service.answer(q)
    except Exception as e:
        lines.append(f"Q: {q!r} -> ERROR {type(e).__name__}: {e}")
        continue
    ns = len(res.sources)
    heads = re.findall(r"\*\*(Answer|Explanation|Example):\*\*", res.answer)
    lines.append(
        f"Q: {q!r} | nsrc={ns} | sections={heads} | "
        f"DEGENERATE={degenerate(res.answer)} | len={len(res.answer)}"
    )
    lines.append("    " + res.answer[:400].replace("\n", " ") + ("..." if len(res.answer) > 400 else ""))

out = "\n".join(lines)
print(out[:6000])
open("scripts/_diag_hunt.txt", "w", encoding="utf-8").write(out)
