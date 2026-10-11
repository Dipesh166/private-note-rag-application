import sys
from app.services import chat_service
from app.prompts import rag_prompts

qs = sys.argv[1:] or ["What is the chunk size used in this project?"]
for q in qs:
    res = chat_service.answer(q)
    print("=" * 70)
    print("Q:", q)
    print("sources:", [(s.filename, s.page, s.score) for s in res.sources])
    print("--- ANSWER ---")
    print(res.answer)
