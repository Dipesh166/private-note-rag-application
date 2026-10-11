from app.services import chat_service

qs = [
    "What is AI engineering?",
    "What is the maximum upload size for this knowledge base?",
    "How does chunking work and why does overlap matter?",
    "What evaluation metrics are recommended for RAG systems?",
    "Tell me about the weather in Paris.",
]
for q in qs:
    res = chat_service.answer(q)
    print("=" * 72)
    print("Q:", q)
    print("nsrc:", len(res.sources), "scores:", [round(s.score, 3) for s in res.sources])
    print("ANS:", res.answer[:800].replace("\n", " "))
