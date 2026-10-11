# Implementation Plan — Local RAG Backend (Start → End)

Written: October 2026 · Scope: **backend + RAG + React frontend**. The API contract (§5) was locked first; the frontend in `Frontend/frontend-private-rag-llm/` now consumes it.

Decisions locked: **Embeddings = `sentence-transformers/all-MiniLM-L6-v2`** · **LLM = `Qwen/Qwen2.5-1.5B-Instruct` via Hugging Face transformers (no Ollama)** · Vector store = Chroma (persistent) · Structure = layered/hexagonal (api → services → infrastructure).

Derived from `Private_Knowledge_Base_Local_RAG_Project_Plan (1).md` and `requirements.txt`.

---

## 1. What we are building

A backend service where a PDF is **not hardcoded**. A file arrives at runtime through an API, gets indexed into a vector store, and is immediately searchable — repeatedly, for any number of PDFs, without restarting the app.

```
STEP A — INGESTION (happens once per document, at runtime)
  client sends file ──► POST /documents/upload
        validate (extension, size, magic bytes)
        sha256 hash  ──► duplicate? return existing doc_id
        load         ──► PyPDFLoader(mode="page")  → 1 Document per page
        chunk        ──► RecursiveCharacterTextSplitter(1000/150) + metadata
        embed        ──► all-MiniLM-L6-v2  (384-dim, local, ~90 MB)
        store        ──► Chroma (data/chroma, persistent) + doc registry
        response 202 {doc_id, status:"processing"}  →  status becomes "ready"

STEP B — QUERYING (happens on every question)
  client sends question ──► POST /chat
        embed question with the SAME model (all-MiniLM-L6-v2)
        Chroma candidate search → cosine relevance floor → MMR selection
        build grounded prompt: [CONTEXT blocks labeled source · page N] + [QUESTION]
        Qwen2.5-1.5B-Instruct (Hugging Face transformers) generates the answer
        respond {answer, sources:[{filename, page, chunk_id, excerpt, score}]}
```

Two properties make it "RAG" instead of "stuff the whole PDF in the prompt":

1. **Ingestion is decoupled from querying** — the file is embedded once; questions only embed the question.
2. **The LLM never sees the whole document** — only the 6 chunks that matched the question, each carrying its filename and page number so the answer is citable.

---

## 2. File structure (industry-standard layered / hexagonal layout)

Dependency rule: **`routes → services → infrastructure`**, with `domain` depending on nothing. Routes never touch Chroma or the LLM directly; services never parse HTTP. Everything external (PDF parser, embeddings, vector DB, LLM) sits behind `infrastructure/` so any of it can be swapped without touching business logic.

```
RAG_pdf_reader_project/
│
├── app/                            # the Python package (import: `app.*`)
│   ├── main.py                     # FastAPI app factory + lifespan (open Chroma, seed .md)
│   ├── config.py                   # pydantic-settings: all env config in one place
│   │
│   ├── api/                        # LAYER 1 — transport (HTTP only)
│   │   ├── router.py               # aggregates /v1/documents, /v1/chat, /v1/health
│   │   ├── deps.py                 # dependency injection (get_store, get_llm, get_settings)
│   │   ├── errors.py               # global exception handlers → {detail, code}
│   │   ├── schemas/                # Pydantic request/response models
│   │   │   ├── document.py         #   UploadResponse, DocumentOut
│   │   │   ├── chat.py             #   ChatRequest, ChatResponse, Source
│   │   │   └── common.py           #   ErrorOut, HealthOut, Page
│   │   └── routes/
│   │       ├── documents.py        #   POST/GET/DELETE /documents
│   │       ├── chat.py             #   POST /chat
│   │       └── health.py           #   GET /health, DELETE /knowledge-base
│   │
│   ├── services/                   # LAYER 2 — use cases / business logic
│   │   ├── ingestion_service.py    #   orchestrate: validate → hash → load → chunk → embed → store
│   │   ├── retrieval_service.py    #   MMR search + score floor → Source objects
│   │   └── chat_service.py         #   retrieve → prompt → generate → citations
│   │
│   ├── domain/                     # LAYER 3 — pure business types (imports nothing)
│   │   ├── models.py               #   Document, Chunk, Source, ChatResult
│   │   ├── enums.py                #   DocumentStatus: processing | ready | failed
│   │   └── constants.py            #   allowed extensions, limits, defaults
│   │
│   ├── infrastructure/             # LAYER 4 — adapters to the outside world
│   │   ├── loaders/
│   │   │   ├── base.py             #   Loader protocol: supports(filename) / load(path)
│   │   │   ├── pdf_loader.py       #   PyPDFLoader(mode="page") → page + source metadata
│   │   │   └── text_loader.py      #   .md / .txt → source metadata
│   │   ├── chunking/
│   │   │   └── recursive_splitter.py   # 1000/150, add_start_index, metadata propagation
│   │   ├── embeddings/
│   │   │   └── minilm_embedder.py  #   all-MiniLM-L6-v2, model bound to collection
│   │   ├── vectorstore/
│   │   │   └── chroma_store.py     #   persistent singleton, upsert, delete_by_doc, count
│   │   ├── llm/
│   │   │   └── hf_client.py        #   transformers singleton, OOM guard, lazy load
│   │   └── registry/
│   │       └── json_registry.py    #   data/registry.json CRUD + status transitions
│   │
│   ├── prompts/
│   │   └── rag_prompts.py          # grounded system prompt + context template
│   └── core/
│       ├── logging.py              # structured logs (request_id, doc_id, timings)
│       └── security.py             # magic-byte sniffing, size cap, safe filenames
│
├── data/                           # runtime artifacts — gitignored
│   ├── uploads/                    # original files (generated names, never client paths)
│   ├── chroma/                     # persisted vectors
│   └── registry.json
│
├── tests/
│   ├── conftest.py                 # fixtures: temp Chroma dir, test app, sample PDF
│   ├── fixtures/sample.pdf
│   ├── unit/
│   │   ├── test_chunker.py         #   metadata survives splitting
│   │   ├── test_indexer.py         #   dedupe, empty-PDF failure, delete-by-doc
│   │   └── test_prompts.py         #   context renders with source labels
│   └── integration/
│       └── test_api.py             #   upload → poll → /chat → assert citation
│
├── scripts/
│   ├── index_sample.py             # Stage 1 checkpoint (no HTTP)
│   └── smoke_cli.py                # Stage 2 checkpoint (end-to-end RAG)
│
├── docs/
│   └── PROJECT_PLAN.md             # the original plan doc (or keep it at root)
│
├── .env.example                    # EMBEDDING_MODEL, LLM_MODEL, paths, limits
├── .gitignore                      # data/, .env, __pycache__, .venv
├── requirements.txt
├── README.md
└── IMPLEMENTATION_PLAN.md          # this file
```

**Rules that keep it clean**

1. `domain/` imports nothing from other layers — it's just types.
2. `routes/` only calls `services/` through `api/deps.py` injection — no Chroma/LLM imports in routes.
3. `services/` depends on protocols (Loader, VectorStore, LLM), implementations live in `infrastructure/` — swapping Chroma for FAISS or transformers for llama-cpp = new adapter file, zero service changes.
4. One config module (`app/config.py`); no `os.getenv` scattered anywhere else.
5. Every directory has `__init__.py`; run as `uvicorn app.main:app` — no `importlib` hacks.
6. Endpoints versioned under `/v1` from day one (`api/router.py` prefixes it), so v2 can coexist later.

---

## 3. Current status (verified 10 October 2026)

Status legend: ✅ complete & verified · 🟡 partial · ⬜ not started

### ✅ Stages 0–3 — DONE

| Stage | Status | Evidence |
| --- | --- | --- |
| 0 — Environment & skeleton | ✅ | `.venv` (Python 3.12), 15 packages, `app/` package imports, `pyflakes` clean |
| 0.4 — Embedding model | ✅ | `all-MiniLM-L6-v2` cached locally, 384-dim |
| 0.5 — Generation model | ✅ | `Qwen/Qwen2.5-1.5B-Instruct` from Hugging Face, 1.54 B params |
| 1 — Ingestion pipeline | ✅ | PDF→3 pages→3 chunks; MD→20 chunks; dedupe, empty-PDF failure, persistence all verified |
| 2 — Retrieval + generation | ✅ | MMR + cosine floor verified; grounded answer with real page citation; honest refusal on out-of-scope question |
| 3 — FastAPI | ✅ | all endpoints live, 13 error paths correct, restart persistence verified |
| 4 — Tests, citation faithfulness & hardening | ⬜ **NEXT** | frontend now complete, so the hold is released; **4.0 (citation fix) blocks the rest** |
| 5 — React frontend | ✅ | React 19 + Vite + **Tailwind v4** + **shadcn/ui**; upload/list/delete + chat with citations; browser-verified end-to-end (Playwright/Edge); `tsc` + `vite build` + `eslint` all exit 0 as of 18:07 |
| — then return to Stage 4 | ⬜ | tests + eval + README |

### Decision: frontend before tests — **now resolved**

Testing (Stage 4) was held while the UI was built. The frontend is complete and
browser-verified (§3), so the hold is **released** and Stage 4 is next.
Rationale at the time: the API contract (§5) was locked and verified, so the
frontend could be built against it; tests written after the UI exists can cover
the full path including UI-driven flows.

**Known risk carried (10 Oct 2026, now closing):** until Stage 4 lands, regressions
are only caught manually via `scripts/api_error_checks.py`, `scripts/smoke_cli.py`
and `scripts/citation_check.py`.

### Live verification results

```
GET /v1/health  → 200 {"status":"ok","llm":true,"llm_device":"cuda",
                       "embedding_model":"all-MiniLM-L6-v2",
                       "indexed_docs":2,"total_chunks":1472}
```

| Check | Result |
| --- | --- |
| Dynamic upload at runtime | ✅ `report.pdf` uploaded via API → `202 processing` → `ready` in <2 s |
| Duplicate detection | ✅ same bytes → `duplicate: true`, no double-indexing |
| `/chat` answer + citation | ✅ "The warranty period is 24 months. [report.pdf · page 1]" |
| Scope filter (`doc_ids`) | ✅ retrieved only from the requested document |
| Deletion removes vectors | ✅ `chroma chunks for deleted doc: 0` (verified against raw Chroma) |
| Restart persistence | ✅ restart → 3 docs / 25 chunks intact |
| Seed idempotency | ✅ no "seeded" log on restart — SHA-256 check skips it |
| Error paths (13) | ✅ 400/404/422 with `{detail, code}` for every case |
| `x-request-id` | ✅ echoed in response headers, present in all logs |
| Lint | ✅ `pyflakes app scripts` exit 0 (10 dead imports found & removed) |
| Compile | ✅ `compileall` exit 0 |

### Browser-level verification (10 Oct 2026, 17:52–18:04)

First time the UI was driven as a real user would, via Playwright + system Edge
against `http://localhost:5173` (Vite proxy → `127.0.0.1:8000`).

| Check | Result |
| --- | --- |
| React mounts, no runtime errors | ✅ `#root` populated, **0** `pageerror` / `console.error` |
| Health badges reflect backend | ✅ "2 docs · 1472 chunks · Cuda · Backend online" |
| Document list from API | ✅ both docs with real stats (535 pages · 1452 chunks) |
| Chat round-trip through UI | ✅ typed question → answer + citation chip rendered in **82 ms** retrieval |
| Cited chunk shows excerpt + score | ✅ 6 source cards, each with page, score, excerpt |
| Upload via file picker | ✅ `sample.pdf` → "accepted — indexing in the background…" → `ready`, 3 pages / 3 chunks |
| Duplicate re-upload in UI | ✅ "already indexed — skipped (SHA-256 match)", row count unchanged |
| Delete via UI | ✅ row removed; other documents untouched; registry back to 2 |
| CORS preflight (real `Origin`) | ✅ `OPTIONS` → 200 + `access-control-allow-origin: http://localhost:5173` |
| Production build | ✅ `tsc -b && vite build` → 330 KB JS (105 KB gzip), 55 KB CSS |

> The earlier `OPTIONS /v1/health → 405` was a **healthcheck probe with no `Origin`
> header**, not a CORS failure. A proper preflight succeeds.

Screenshots: `docs/ui-screenshot.png`, `docs/ui-chat-answer.png`,
`docs/ui-upload.png`, `docs/ui-after-delete.png`.

### ⚠️ Open defect: citation can point at the wrong chunk

Found by `scripts/citation_check.py`, which prints the answer **beside the full text
of the chunk it cites** so faithfulness can be judged directly.

| Question | Answer | Cited | Verdict |
| --- | --- | --- | --- |
| What embedding model does this project use? | "Sentence Transformers all-MiniLM-L6-v2" | `AI Engineering.pdf · page 91` — excerpt is about *Mamba/Jamba layers* | ❌ **unfaithful** — the real support is the plan `.md`, rank #4 |
| What is retrieval augmented generation? | RAG definition | `AI Engineering.pdf · page 278` — "The term retrieval-augmented generation was coined in…" | ✅ faithful |
| How are documents split into chunks? | chunking by chars/words/sentences | `AI Engineering.pdf · page 292` — "Chunking strategy…" | ✅ faithful |

**1 of 3 failed.** `normalize_citations()` is *not* the culprit — it correctly
canonicalises the *format*. The failure is upstream: the 1.5 B model **copies one
block's label while answering from another block's content**. It appears specifically
when the true evidence sits mid-ranking (rank #4, score 0.412) while a higher-ranked
but irrelevant chunk sits above it.

Because "answers with page-level citations" is the product's core promise, this is
treated as a **blocker for Stage 4**, not a nice-to-have.

### Minor findings (not bugs, worth a decision)

| # | Finding | Why it matters |
| --- | --- | --- |
| M1 | `handleDelete` deletes with **no confirmation**, while "Clear all" has one | deletion is irreversible — the source file is already `unlink()`ed after indexing |
| M2 | `sources` is still returned when the answer is `Insufficient context…` | UI renders citation chips for a refusal, implying that page supports it |
| M3 | Sources display in MMR order, not score order, but are labelled `#1…#6` | `#4` (0.412) can outrank `#2` (0.393) — looks like a ranking bug, isn't |


### Performance (GTX 1650 Ti, CUDA 13.0, fp16)

| Metric | CPU | GPU |
| --- | --- | --- |
| Steady-state answer | 7.5–37 s | **3.3–11.8 s** |
| 4-question suite | 69.5 s | 45.1 s |
| Retrieval | ~25 ms | ~25 ms |
| First call (includes model load) | ~7 s | ~30 s (3 GB VRAM transfer) |

> GPU gives **~2×**, not the 5–10× initially hoped: the 1650 Ti has no Tensor Cores
> (TU117), so fp16 yields ~2× rather than the 4–8× Tensor Cores would.

### Bugs found during the build — 11 fixed, 1 open

| # | Bug | Impact if shipped |
| --- | --- | --- |
| 1 | MMR fed Chroma **distances** as relevance scores | retrieval returned *least* relevant chunks while looking healthy |
| 2 | `min_score` compared against a distance, not relevance | relevance floor never fired |
| 3 | MMR index misalignment after filtering | citations pointed at wrong chunks |
| 4 | `apply_chat_template` returns `BatchEncoding` in transformers 5.x | `generate()` crashed |
| 5 | Deprecated `torch_dtype` | warnings |
| 6 | Citations showed generated storage name, not original filename | useless citations |
| 7 | `reset()` reassigned a local instead of the singleton | stale store after KB clear |
| 8 | PyPI Windows torch wheels are CPU-only | **GPU silently unused** (twice) |
| 9 | `set[str]` settings field JSON-decrumbed from `.env` | app failed to boot |
| 10 | `if False else` / dead imports (10 found by pyflakes) | dead code |
| **11** | **OPEN** — model cites a chunk that does not support its answer (1 of 3 probes) | **citations unfaithful — the product's core promise** (see §3 "Open defect") |
| 12 | `source-dialog.tsx:45` `react-hooks/set-state-in-effect` failed lint | ✅ **fixed** in a concurrent edit at 18:06 — `npm run lint` exit 0 |

---

## 4. End-to-end build order

Every step has a **checkpoint** you can verify before moving on. Do them in order; nothing is skipped.

> **✅ Stages 0–3 complete and verified (10 Oct 2026).** See §3 for evidence.

### STAGE 0 — Environment & skeleton ✅

| # | Task | Checkpoint |
| --- | --- | --- |
| 0.1 | Verify `.venv`; `pip install -r requirements.txt`; **add `pydantic-settings`** | `pip list` shows fastapi, langchain-chroma, langchain-huggingface, transformers, pypdf, python-multipart, pydantic-settings |
| 0.2 | Create the structure in §2 with all `__init__.py` files | `python -c "import app"` succeeds |
| 0.3 | `app/config.py` + `.env.example` — `EMBEDDING_MODEL=all-MiniLM-L6-v2`, `LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct`, `LLM_DEVICE=auto`, `CHROMA_DIR=data/chroma`, `UPLOAD_DIR=data/uploads`, `MAX_UPLOAD_MB=20`, `TOP_K=6`, `FETCH_K=20`, `LAMBDA_MULT=0.25`, `MIN_SCORE` | config loads from `.env` |
| 0.4 | Download the embedding model once (first call caches it locally) | `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` |
| 0.5 | Download the LLM from Hugging Face: `Qwen/Qwen2.5-1.5B-Instruct` via transformers | model loads (1.54 B params) |

### STAGE 1 — Ingestion pipeline (built as plain functions first) ✅

| # | Task | Checkpoint |
| --- | --- | --- |
| 1.1 | `infrastructure/loaders/` — `PdfLoader` (`PyPDFLoader(path, mode="page")`, each Document gets `page` + `source`), `TextLoader` for `.md`/`.txt` (gets `source`) | 3-page test PDF → 3 Documents with correct `page` |
| 1.2 | `infrastructure/chunking/recursive_splitter.py` — `RecursiveCharacterTextSplitter(1000, 150, add_start_index=True)`; attach `doc_id`, `chunk_id`, `source`, `page` to every chunk | **Unit test green:** metadata survives splitting |
| 1.3 | `infrastructure/embeddings/minilm_embedder.py` — one `HuggingFaceEmbeddings("all-MiniLM-L6-v2")` instance reused for documents **and** queries; expose `model_name` for collection binding | embed("hello") → 384-dim vector |
| 1.4 | `infrastructure/vectorstore/chroma_store.py` — persistent singleton (`langchain_chroma.Chroma`, `persist_directory=data/chroma`), `upsert`, `delete_by_doc(doc_id)`, `count()`; **store `EMBEDDING_MODEL` in collection metadata and refuse to open with a mismatched model** | count survives a restart; wrong model → clear error |
| 1.5 | `infrastructure/registry/json_registry.py` — `{doc_id, filename, sha256, pages, chunks, status, error, ingested_at}` | status transitions processing → ready/failed |
| 1.6 | `services/ingestion_service.py` — hash → dedupe → load → chunk → embed → upsert → register; **empty extraction (scanned PDF) → `failed` with reason** | run twice on same file → `duplicate: true`, chunk count unchanged |
| 1.7 | `scripts/index_sample.py` | **Checkpoint:** a real PDF is indexed, `count() > 0` |

### STAGE 2 — Retrieval + generation (the answering half) ✅

| # | Task | Checkpoint |
| --- | --- | --- |
| 2.1 | `services/retrieval_service.py` — MMR (`k=6, fetch_k=20, lambda_mult=0.25`) + `MIN_SCORE` floor → `Source(doc_id, filename, page, chunk_id, excerpt, score)` | question about page 2 → chunks with `page == 2` |
| 2.2 | `prompts/rag_prompts.py` — context is reference material, not instructions; answer only from context; admit when missing; cite `[source · page N]` | prompt renders with labeled blocks |
| 2.3 | `infrastructure/llm/hf_client.py` + `services/chat_service.py` — lazy model load, OOM guard, `insufficient_context` when retrieval weak | out-of-scope question → honest "I don't know" |
| 2.4 | `scripts/smoke_cli.py` — index → ask N questions → print answer + page citations | **Checkpoint / Milestone 1:** grounded answer with real page numbers |

### STAGE 3 — FastAPI (the "dynamic" part) ✅

| # | Task | Checkpoint |
| --- | --- | --- |
| 3.1 | `api/schemas/` — `UploadResponse`, `DocumentOut`, `ChatRequest` (question 3–1000 chars, optional `doc_ids`, `top_k`), `ChatResponse`, `Source`, `ErrorOut` | invalid input → 422 with clear detail |
| 3.2 | `app/main.py` — app factory + lifespan: reopen Chroma, **seed the bundled plan `.md` on first startup** (skip if its hash is in registry) | restart → indexed docs still counted |
| 3.3 | `api/deps.py` + `api/router.py` — DI wiring, `/v1` prefix | app boots, routes visible in `/docs` |
| 3.4 | `api/routes/documents.py` — `POST /documents/upload` (multipart, validate, save as generated name, `202`, index via `BackgroundTasks`), `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}` | upload in `/docs` → `202` → poll → `ready` |
| 3.5 | `api/routes/chat.py` + `health.py` — `/chat` returns answer + sources + `retrieval_ms`; `/health` → `{status, llm, embedding_model, indexed_docs}`; `DELETE /knowledge-base?confirm=true` | Swagger call returns cited answer |
| 3.6 | `api/errors.py` + `core/security.py` + `core/logging.py` — `400` invalid upload (type/size/magic), `404` unknown doc, `422` schema, `500/503` server/LLM; magic-byte sniffing; safe filenames; logs with `request_id`/`doc_id` | **verified: 13/13 error paths correct** |

**Checkpoint for Stage 3:** API works standalone — `uvicorn app.main:app`, upload + ask via `/docs`, citations returned. **This is your deliverable; the frontend plugs into these endpoints later.**

### STAGE 4 — Tests, citation faithfulness & hardening ← **NEXT**

| # | Task | Checkpoint |
| --- | --- | --- |
| **4.0** | **Fix citation faithfulness** — the model cites a chunk that does not support its answer (§3 "Open defect", 1 of 3 probes). Verify the chosen citation against the retrieved chunk texts *in code* instead of trusting the 1.5 B model's label; `scripts/citation_check.py` is the harness | 3/3 probes faithful |
| 4.1 | `tests/unit/` — chunker metadata, indexer dedupe/empty-PDF/delete, prompt rendering, citation normalizer | `pytest` green |
| 4.2 | `tests/integration/test_api.py` — upload fixture PDF → poll → `/chat` → assert citation matches | `pytest` green |
| 4.3 | Evaluation set: ~15 questions with expected pages; measure **retrieval hit-rate separately from answer correctness**; tune `chunk_size`, `top_k`, `lambda_mult` against it | numbers recorded |
| 4.4 | Security pass: generated filenames, size cap, doc text as untrusted prompt data, Chroma not publicly exposed | checklist done |
| 4.5 | README: setup, model download, `curl` API examples, architecture diagram, privacy note (100% local) | someone else runs it from the README |
| 4.6 | Frontend polish: decide on minor findings M1–M3 (§3) — delete confirm dialog, `sources` on refusal, MMR-vs-score display order | `npm run lint` stays exit 0 |

**Proposed order for Stage 4 (next work):**

0. **Citation faithfulness fix first** — everything else in Stage 4 measures quality
   *through* citations, so an unfaithful citation would poison every later number.
   Candidate approaches, cheapest first:
   - **a. Verify in code:** after generation, score each retrieved chunk against the
     answer text (token overlap, or the embedding model already loaded) and re-point
     the citation to the best-supported chunk. Deterministic, no new dependency.
   - **b. Numeric block citation:** prompt for `[4]` instead of asking a 1.5 B model to
     copy a long filename string; `normalize_citations` already maps `Block N`
     positionally, so only the prompt changes.
   - Re-run `scripts/citation_check.py` after each change — it prints the answer beside
     the cited chunk's full text, so regressions are obvious by eye.
1. **`tests/unit/test_chunker.py`** — metadata survives splitting; `chunk_id` format; empty chunk raises. *(fast, no model)*
2. **`tests/unit/test_citations.py`** — the 6 normalizer cases already proven manually, locked in as tests.
3. **`tests/unit/test_security.py`** — `.exe` rejected, magic bytes caught, size cap, generated filenames.
4. **`tests/unit/test_indexer.py`** — dedupe, empty-PDF → `failed`, `delete_by_doc` → 0 chunks.
5. **`tests/conftest.py`** — temp Chroma dir + temp registry so tests never touch `data/`.
6. **`tests/integration/test_api.py`** — FastAPI `TestClient`: upload → poll → `/chat` → assert `sources[0].page`.
7. **`tests/eval/questions.yaml`** — 15 questions with expected doc+page; script reports retrieval hit-rate vs answer correctness separately.
8. **Tune** `chunk_size` / `top_k` / `lambda_mult` against those numbers, record the winner in §6.
9. **Security checklist** — prompt-injection PDF (a PDF that says "ignore previous instructions"), oversized file, Chroma bound to `127.0.0.1`.
10. **`README.md`** — setup, model downloads, `curl` examples, architecture diagram, privacy note.

### STAGE 5 — React frontend ✅

React UI in `Frontend/frontend-private-rag-llm/` consuming §5's contract: drag-and-drop
upload → `POST /v1/documents/upload` → status polling, chat → `POST /v1/chat` → citation
cards with filename · page · score, document list → `GET/DELETE /v1/documents`, plus
`GET /v1/health` badges in the header and `DELETE /v1/knowledge-base` behind a confirm
dialog.

| # | Task | Status |
| --- | --- | --- |
| 5.1 | Scaffold: Vite + React 19 + TypeScript (`@` alias → `src/`) | ✅ |
| 5.2 | **Tailwind CSS v4** via `@tailwindcss/vite` + `@import "tailwindcss"` in `src/index.css` | ✅ verified — build emits 42 kB CSS with utilities |
| 5.3 | **shadcn/ui** (style `radix-nova`, base `neutral`): button, card, input, textarea, badge, scroll-area, alert, separator, skeleton, dialog, select in `src/components/ui/` | ✅ |
| 5.4 | Typed API client `src/lib/api.ts` mirroring the §5 schemas incl. the `{detail, code}` error envelope | ✅ |
| 5.5 | Documents panel: drag-drop/click upload, 2.5 s status polling while `processing`, per-doc delete, clear-all (dialog + `confirm=true`) | ✅ |
| 5.6 | Chat panel: suggestions, Enter-to-send, loading state, citation cards, per-document scope filter (`doc_ids`) | ✅ |
| 5.7 | Health header: online/offline, docs, chunks, llm device (20 s poll) | ✅ |
| 5.8 | Dev proxy `/v1 → 127.0.0.1:8000` in `vite.config.ts` **+ CORS middleware on the backend** (`CORS_ORIGINS`, default `localhost:5173`) | ✅ |
| 5.9 | Cleanup: stray `Frontend/package.json` + `Frontend/node_modules` (tailwind had been installed one level too high), Vite starter demo (counter/logos/App.css/hero), scaffold assets | ✅ |

**Frontend bugs found & fixed during the build (5):**

| # | Bug | Impact if shipped |
| --- | --- | --- |
| 1 | `@tailwindcss/vite` imported in `vite.config.ts` but installed in `Frontend/` (wrong dir), absent from the app's `node_modules` | `npm run dev` crashed — "Cannot find package '@tailwindcss/vite'" |
| 2 | `src/index.css` had no `@import "tailwindcss"` | zero utilities generated — Tailwind silently dead |
| 3 | `@vitejs/plugin-react` in devDeps but never registered in `vite.config.ts` | no React Fast Refresh |
| 4 | Backend had no CORS middleware | browser blocked every `localhost:8000` call if not proxied |
| 5 | `shadcn init` (latest CLI) has Windows path bugs: wrote components into a literal `@\components\ui\` dir and aborted before writing the theme CSS | unusable install — components moved to `src/components/ui/`, theme assembled from the official registry palette (`ui.shadcn.com/r/colors/neutral.json`) |

**Verification:** `tsc -b && vite build` green · `eslint .` 0 errors · built CSS contains
`.bg-background`, `.flex`, `.animate-spin` utilities · `pyflakes app` + `compileall` exit 0 ·
live smoke: backend on `:8000` + Vite on `:5173`, proxy + CORS chain confirmed.

**Next:** return to Stage 4 (tests, eval, security, README).

---

## 5. API contract (what the frontend will call later)

| Method / endpoint | Body / params | Returns |
| --- | --- | --- |
| `POST /v1/documents/upload` | multipart `file` (`.pdf`, `.md`, `.txt`) | `202 {doc_id, filename, status, duplicate:false}` · duplicate content → `202 {duplicate:true}` |
| `GET /v1/documents` | — | `{documents:[{doc_id, filename, status, pages, chunks, ingested_at, error?}], total}` |
| `GET /v1/documents/{doc_id}` | — | single document status (poll during indexing) · `404` unknown |
| `DELETE /v1/documents/{doc_id}` | — | `200 {detail, removed}` · `404` unknown |
| `POST /v1/chat` | `{question, doc_ids?, top_k?}` | `{answer, sources[], retrieval_ms, model}` |
| `DELETE /v1/knowledge-base?confirm=true` | — | `200 {detail, removed}` — refuses unless `confirm=true` |
| `GET /v1/health` | — | `{status, llm, llm_device, embedding_model, indexed_docs, total_chunks}` |

**Error envelope:** every non-2xx returns `{detail, code}` — `400` invalid upload (type/size/magic bytes), `404` unknown doc, `422` schema violation, `500` internal, `503` generation unavailable.

---

## 6. Design decisions (locked + swappable)

| Decision | Locked value | Alternative / note |
| --- | --- | --- |
| **Embeddings** | **`sentence-transformers/all-MiniLM-L6-v2`** (384-dim, ~90 MB, fast) | `BAAI/bge-small-en-v1.5` scores ~+6 MTEB and is the A/B candidate in Stage 4.3 — **requires full reindex**, the collection stores its model name and refuses a mismatch |
| Chunking | Recursive 1000 chars / 150 overlap | token-based (`tiktoken`) or semantic chunking |
| Retrieval | MMR k=6, fetch_k=20, λ=0.25 + `MIN_SCORE` floor | add cross-encoder rerank (`bge-reranker-base`) after MMR if eval demands |
| **LLM** | **`Qwen/Qwen2.5-1.5B-Instruct`** via HF transformers (local, CPU) | Larger Qwen (3B/7B) if answers are too weak; GGUF + llama-cpp-python for speed. Ollama was uninstalled by decision — HF is the single model source. |
| Vector store | Chroma, persistent | FAISS/Qdrant behind the same `VectorStore` protocol |
| Indexing job | FastAPI `BackgroundTasks` | Celery/RQ under heavy load |
| Doc registry | `data/registry.json` | SQLite when concurrent writes matter |
| Dedupe | SHA-256 of file bytes | weaker: name+size metadata |

---

## 7. Dependencies

`requirements.txt` already covers the stack. **Add one package:**

```
pydantic-settings        # typed config loaded from .env
```

Use `langchain_chroma.Chroma`, not the deprecated `langchain_community.vectorstores.Chroma`.

---

## 8. Definition of done (this phase)

### Verified ✅

- [x] Any PDF or `.md` uploaded at runtime is indexed and immediately searchable — no restart.
- [x] Re-uploading the same file is detected by SHA-256 and skipped (`duplicate: true`).
- [x] `GET /v1/documents` shows status; deleting removes that doc's chunks only (verified `0` left in Chroma).
- [x] Chroma persists across restarts; startup reopens the collection and validates the embedding model.
- [x] `POST /v1/chat` returns an answer **with filename + page citations**, and an honest "insufficient context" when retrieval is weak.
- [x] The bundled plan `.md` is seeded on first startup and answerable — and *not* re-seeded on restart.
- [x] Empty/scanned PDFs are marked `failed` with a visible reason.
- [x] `GET /v1/health` reports LLM readiness, device (cuda), embedding model, and indexed-document count.
- [x] 13 error paths return consistent `{detail, code}` envelopes.
- [x] `pyflakes` clean; `compileall` clean.

### Still to do ⬜ (Stage 4)

- [ ] Tests green: chunk metadata, dedupe, prompt rendering, one end-to-end upload→ask.
- [ ] Evaluation set (~15 questions) with retrieval hit-rate measured separately from answer correctness.
- [ ] Security pass: size cap under load, Chroma not publicly exposed, prompt-injection test.
- [ ] README with setup, `curl` examples, architecture diagram, privacy note.

### Frontend ✅ (Stage 5, 10 October 2026)

- [x] Tailwind CSS v4 verified working (build emits real utilities; was broken — wrong-dir install + missing `@import`).
- [x] shadcn/ui installed (radix-nova · neutral) — 11 primitives in `src/components/ui/`.
- [x] Scaffold cruft removed: stray `Frontend/package.json` + `node_modules`, Vite demo app, `App.css`, hero/logos/icons.
- [x] Upload (drag-drop), indexing-status polling, per-doc delete, clear-all behind confirm dialog.
- [x] Chat with grounded answers + filename · page · score citation cards; per-document scope filter.
- [x] Health header (online/offline, docs, chunks, cuda/cpu) polled every 20 s.
- [x] Backend integrated: typed client mirrors §5 exactly; dev proxy + CORS; `{detail, code}` errors surfaced in the UI.
- [x] `tsc` + `vite build` green, `eslint` 0 errors.

---

## 9. How to run (backend + frontend)

### Backend — FastAPI on http://127.0.0.1:8000

From the repo root (`RAG_pdf_reader_project/`), using the existing `.venv` (Python 3.12):

```powershell
# one-time: install deps (if .venv is fresh)
.venv\Scripts\pip install -r requirements.txt

# run the API
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Linux/macOS: `source .venv/bin/activate && uvicorn app.main:app --reload`

- Swagger UI: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/v1/health
- On first startup the bundled plan `.md` is seeded automatically (index it once, ~seconds).
- CORS: the React dev origin (`http://localhost:5173`) is allowed via `CORS_ORIGINS`
  in `.env` (see `.env.example`) — a fallback, since the Vite dev server proxies `/v1` itself.

### Frontend — Vite on http://localhost:5173

In a **second terminal**, from `Frontend/frontend-private-rag-llm/`:

```powershell
# one-time: install deps
npm install

# run the dev server (backend must already be running on :8000)
npm run dev
```

Open http://localhost:5173 — the header shows **Backend online** when the chain works.
Production build: `npm run build` (output in `dist/`, preview with `npm run preview`;
point `VITE_API_BASE` at the backend if serving it separately).

### Quick check

1. `curl http://127.0.0.1:8000/v1/health` → `{"status":"ok",...}`
2. Open http://localhost:5173 → upload a `.pdf` → status flips `processing → ready`
3. Ask a question → answer arrives with `filename · page N` citation cards.
