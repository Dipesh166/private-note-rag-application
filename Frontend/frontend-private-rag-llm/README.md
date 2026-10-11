# Private Knowledge Base — Frontend

React 19 + Vite + TypeScript + **Tailwind CSS v4** + **shadcn/ui** (radix-nova style).
Consumes the local RAG backend defined in `../../IMPLEMENTATION_PLAN.md` §5.

## What it does

| Panel | Actions |
| --- | --- |
| **Documents** | drag-and-drop or click-to-browse upload (`.pdf` / `.md` / `.txt`), live indexing status (polls `GET /v1/documents` every 2.5 s while `processing`), delete one, clear the whole knowledge base (confirmed via dialog) |
| **Chat** | ask questions → `POST /v1/chat` → grounded answer with **filename · page · score** citation cards; optional per-document scope filter; suggested starter questions |
| **Header** | live backend health (`GET /v1/health` every 20 s): online/offline, indexed docs, chunks, LLM device (cuda/cpu) |

## Stack & layout

```
src/
├── main.tsx                  # root render (StrictMode)
├── App.tsx                   # layout + health/document polling
├── index.css                 # Tailwind v4 + shadcn theme (radix-nova · neutral)
├── lib/api.ts                # typed client for /v1 (mirrors backend Pydantic schemas)
└── components/
    ├── app-header.tsx        # health badges
    ├── document-panel.tsx    # upload + list + delete + clear-all
    ├── chat-panel.tsx        # messages + citations + scope filter
    └── ui/                   # shadcn/ui primitives (button, card, dialog, …)
```

- **API access:** dev requests go to the same origin and Vite proxies `/v1` →
  `http://127.0.0.1:8000` (see `vite.config.ts`), so there is **no CORS friction in
  dev**. The backend also allows `http://localhost:5173` via `CORS_ORIGINS` as a
  fallback. For a custom backend URL, set `VITE_API_BASE` (e.g.
  `VITE_API_BASE=http://127.0.0.1:8000 npm run dev`).
- **shadcn/ui:** components live in `src/components/ui` — edit them freely, they are
  yours. Add more with `npx shadcn@latest add <component>`.

## Commands

```bash
npm install        # first time only
npm run dev        # dev server → http://localhost:5173  (backend must run on :8000)
npm run build      # tsc + vite build → dist/
npm run preview    # serve the production build locally
npm run lint       # eslint
```

The backend must be running first — see the root `IMPLEMENTATION_PLAN.md` §9 for
backend commands.
