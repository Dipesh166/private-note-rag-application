import re
from app.config import get_settings
from app.services import chat_service

QS = [
    ("Explain chunking in great detail.", 20),
    ("What is RAG?", 20),
    ("Summarize this entire knowledge base.", 20),
    ("Tell me everything about AI Engineering.", 20),
    ("What is the maximum upload size?", 20),
    ("What is vector search?", 6),
    ("How do I deploy this?", 6),
]

def degenerate(s):
    if re.search(r"(.)\1{19,}", s):
        return True
    if len(s) > 60 and len(set(s)) < 8:
        return True
    return False

lines = []
for q, k in QS:
    try:
        res = chat_service.answer(q, top_k=k)
    except Exception as e:
        lines.append(f"Q={q!r} k={k} ERROR {type(e).__name__}: {e}")
        continue
    heads = re.findall(r"\*\*(Answer|Explanation|Example):\*\*", res.answer)
    deg = degenerate(res.answer)
    lines.append(f"Q={q!r} k={k} nsrc={len(res.sources)} secs={heads} DEGEN={deg} len={len(res.answer)}")
    lines.append("    " + res.answer[:350].replace("\n", " "))
    if deg:
        lines.append("    !!! DEGENERATED FULL: " + res.answer[:1500])

out = "\n".join(lines)
open("scripts/_diag_stress.txt", "w", encoding="utf-8").write(out)
print(out[:7000])
