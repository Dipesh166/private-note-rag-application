import type { ReactNode } from 'react'

import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  Braces,
  CheckCircle2,
  Cpu,
  Database,
  FileText,
  Filter,
  Layers,
  Lock,
  Quote,
  Scissors,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Upload,
  Zap,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from 'cn'

import type { HealthOut } from '@/lib/api'

interface AboutPanelProps {
  health: HealthOut | null
}

export function AboutPanel({ health }: AboutPanelProps) {
  return (
    <div className="flex flex-col gap-4 pb-8">

      <section className="relative overflow-hidden rounded-2xl border border-border bg-card/70 p-5 ring-1 ring-foreground/10 lg:p-7">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 -right-20 size-64 rounded-full bg-violet-500/20 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -bottom-24 size-64 rounded-full bg-blue-500/15 blur-3xl"
        />

        <div className="absolute top-5 right-5 hidden size-20 overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600 via-indigo-500 to-blue-600 shadow-xl shadow-indigo-500/30 ring-1 ring-white/10 sm:block">
          <img
            src="/logo.png"
            alt="Private Knowledge Base logo"
            className="size-full scale-125 object-contain"
          />
        </div>

        <div className="relative flex flex-col gap-3 sm:pr-24">
          <Badge className="w-fit">
            <Sparkles className="size-3" />
            About this project
          </Badge>
          <h2 className="text-xl font-semibold tracking-tight lg:text-2xl">
            A private knowledge base with Retrieval-Augmented Generation
          </h2>
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
            Upload a PDF and ask questions about it. The system finds the passages that
            actually answer your question, hands <em>only those</em> to a local LLM, and
            returns a grounded reply with a <span className="text-foreground">[filename · page N]</span>{' '}
            citation for every claim. Embeddings, vector search and generation all run on this
            machine, so no cloud API ever sees your documents.
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {['FastAPI', 'LangChain', 'ChromaDB', 'all-MiniLM-L6-v2', 'Qwen2.5-1.5B', 'React + Vite'].map(
              (t) => (
                <Badge key={t} variant="secondary">
                  {t}
                </Badge>
              ),
            )}
          </div>

          {health && (
            <dl className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Embedding model" value={health.embedding_model} />
              <Stat label="Generator" value="Qwen2.5-1.5B (local)" />
              <Stat label="Runs on" value={health.llm_device.toUpperCase()} />
              <Stat
                label="Index"
                value={`${health.indexed_docs} docs · ${health.total_chunks} chunks`}
              />
            </dl>
          )}
        </div>
      </section>

      <Section
        icon={<Zap className="size-4" />}
        title="How it works: two decoupled pipelines"
        description="Documents are embedded once at upload time; questions are embedded only when asked. That separation is what makes it RAG instead of 'paste the whole PDF into the prompt'."
      >
        <div className="grid gap-3 lg:grid-cols-2">
          <Pipeline
            tone="blue"
            stepIcon={<Upload className="size-3.5" />}
            heading="Ingestion: once per document"
            caption="POST /v1/documents/upload → 202, indexing continues in a background task"
            steps={[
              {
                icon: <ShieldCheck className="size-3.5" />,
                title: 'Validate the upload',
                text: 'Extension allow-list (.pdf/.md/.txt), 20 MB cap and a magic-byte check, then a SHA-256 hash so an identical re-upload short-circuits as a duplicate.',
              },
              {
                icon: <FileText className="size-3.5" />,
                title: 'Load page by page',
                text: 'PyPDFLoader in page mode produces one document per page and converts to 1-based page numbers, the foundation of every citation.',
              },
              {
                icon: <Scissors className="size-3.5" />,
                title: 'Chunk: 1000 chars, 150 overlap',
                text: 'A recursive character splitter breaks on \\n\\n, \\n, sentence, then word. Each chunk keeps doc_id, chunk_id, source filename and page.',
              },
              {
                icon: <Boxes className="size-3.5" />,
                title: 'Embed with MiniLM-L6-v2',
                text: '384-dimension vectors, L2-normalized so cosine similarity equals a dot product. One shared model instance serves documents and queries.',
              },
              {
                icon: <Database className="size-3.5" />,
                title: 'Persist to Chroma',
                text: 'Vectors upsert by stable chunk_id (re-ingesting replaces, never doubles) into a persistent collection, and the registry flips processing → ready.',
              },
            ]}
          />

          <Pipeline
            tone="violet"
            stepIcon={<Search className="size-3.5" />}
            heading="Query: on every question"
            caption="POST /v1/chat → retrieve → prompt → generate → cite"
            steps={[
              {
                icon: <Braces className="size-3.5" />,
                title: 'Embed the question once',
                text: 'The same embedding model is reused for queries, and the vector is shared by the candidate search and the scoring pass.',
              },
              {
                icon: <Layers className="size-3.5" />,
                title: 'Fetch 20 candidates',
                text: 'Chroma returns the nearest chunks (optionally scoped to selected documents) as a raw distance, used for ordering only and never as a score.',
              },
              {
                icon: <Filter className="size-3.5" />,
                title: 'Score floor: drop below 0.20',
                text: 'True cosine relevance is recomputed from stored vectors; anything weaker is discarded, because irrelevant context breeds confident hallucinations.',
              },
              {
                icon: <ArrowRight className="size-3.5" />,
                title: 'MMR selection (λ = 0.25)',
                text: 'Maximal Marginal Relevance balances relevance against diversity, so the model gets six genuinely different useful passages instead of six copies of one.',
              },
              {
                icon: <Cpu className="size-3.5" />,
                title: 'Generate locally, then cite',
                text: 'Qwen2.5-1.5B decodes greedily (temperature 0) from a labelled context, and the citations are canonicalized in code against the real retrieval results.',
              },
            ]}
          />
        </div>
      </Section>

      <Section
        icon={<ShieldCheck className="size-4" />}
        title="How answers stay trustworthy"
        description="Retrieval quality alone is not enough: the prompt, the decoder and the response path are all built to resist hallucination."
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Feature
            icon={<Quote className="size-4 text-primary" />}
            title="Citations computed in code"
            text="The model's own citation formatting is unreliable at 1.5B params, so every label is rewritten against the authoritative source list before the response is sent."
          />
          <Feature
            icon={<AlertTriangle className="size-4 text-amber-400" />}
            title="It is allowed to say 'I don't know'"
            text="If nothing clears the relevance floor, the reply is exactly “Insufficient context to answer this question.” instead of an invented answer."
          />
          <Feature
            icon={<Lock className="size-4 text-emerald-400" />}
            title="Prompt-injection hardened"
            text="Document text is passed strictly as data with an explicit instruction to ignore any commands hidden inside it; question and context are separate blocks."
          />
          <Feature
            icon={<Database className="size-4 text-sky-400" />}
            title="Bounded context window"
            text="Context is capped at 8,000 characters no matter how many chunks match, keeping prompts cheap and latency predictable."
          />
          <Feature
            icon={<Boxes className="size-4 text-violet-400" />}
            title="Model binding guard"
            text="The embedding model name is stamped into the collection metadata; opening it with a different model raises instead of silently returning garbage scores."
          />
          <Feature
            icon={<Zap className="size-4 text-teal-400" />}
            title="Fast where it matters"
            text="Uploads answer instantly (indexing runs in the background) and the heavy models warm up on a daemon thread, so the server binds the port immediately."
          />
        </div>
      </Section>

      <Section
        icon={<Layers className="size-4" />}
        title="Architecture: layered, with one dependency rule"
        description="routes → services → infrastructure, and the domain layer imports nothing. Every external system sits behind an adapter so it can be swapped without touching business logic."
      >
        <div className="flex flex-col gap-2">
          <LayerRow
            name="api/"
            role="Transport"
            text="FastAPI routes, Pydantic request/response schemas, dependency injection and a consistent {detail, code} error envelope. Never touches Chroma or the LLM directly."
          />
          <LayerRow
            name="services/"
            role="Use cases"
            text="ingestion_service (validate → hash → load → chunk → embed → store), retrieval_service (floor + MMR), chat_service (retrieve → prompt → generate → cite)."
          />
          <LayerRow
            name="domain/"
            role="Pure types"
            text="Document, Source, ChatResult, DocumentStatus and shared constants, imported by nothing from any other layer."
          />
          <LayerRow
            name="infrastructure/"
            role="Adapters"
            text="PDF/text loaders, the recursive splitter, the MiniLM embedder, the persistent Chroma store, the transformers LLM client and the JSON document registry."
          />
          <LayerRow
            name="prompts/"
            role="Grounding"
            text="The system prompt, the labelled context template and the citation normalizer that canonicalizes whatever the model emitted."
          />
        </div>
      </Section>

      <Section
        icon={<Braces className="size-4" />}
        title="Tuning knobs"
        description="Every quality lever is configuration, not code: tune against an eval set without touching the pipeline."
      >
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">Setting</th>
                <th className="px-3 py-2 font-medium">Default</th>
                <th className="hidden px-3 py-2 font-medium sm:table-cell">Effect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card/50">
              {[
                ['chunk_size / chunk_overlap', '1000 / 150', 'Bigger chunks keep arguments intact; overlap keeps split sentences whole.'],
                ['top_k / fetch_k', '6 / 20', 'How many chunks are returned vs. how many candidates are considered.'],
                ['lambda_mult (MMR)', '0.25', 'Lower = more diverse context, higher = stick closer to pure relevance.'],
                ['min_score', '0.20', 'Cosine floor: the abstain threshold when nothing matches.'],
                ['llm_temperature', '0.0', 'Greedy decoding: the same question yields the same answer.'],
                ['llm_max_new_tokens', '768', 'Length budget for the three-part answer.'],
                ['max_context_chars', '8000', 'Hard cap on prompt size, regardless of retrieved chunks.'],
              ].map(([setting, value, effect]) => (
                <tr key={setting} className="align-top">
                  <td className="px-3 py-2 font-mono text-xs text-foreground">{setting}</td>
                  <td className="px-3 py-2 font-mono text-xs text-primary">{value}</td>
                  <td className="hidden px-3 py-2 text-xs text-muted-foreground sm:table-cell">
                    {effect}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        icon={<CheckCircle2 className="size-4" />}
        title="Why this design wins"
      >
        <div className="grid gap-2.5 sm:grid-cols-2">
          {[
            ['Verifiable answers', 'Every claim maps to a real file and page you can open in one click.'],
            ['Hallucination-resistant', 'Only relevant chunks reach the model, with a refusal path when evidence is missing.'],
            ['Private by default', 'Embeddings, search and generation never leave this machine, so it is safe for regulated documents.'],
            ['Cheap to run', 'A 90 MB embedder plus a 1.5B model (fp16 ≈ 3 GB VRAM): no API bills, no rate limits.'],
            ['Scales with documents, not prompts', 'Answer cost depends on 6 chunks, never on how large the corpus grows.'],
            ['Incremental knowledge', 'Upload, re-upload and delete at runtime: there is never a need to re-index the world.'],
          ].map(([title, text]) => (
            <div
              key={title}
              className="flex gap-2.5 rounded-xl border border-border bg-card/50 p-3"
            >
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-400" />
              <div>
                <p className="text-sm font-medium">{title}</p>
                <p className="text-xs leading-relaxed text-muted-foreground">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <p className="text-center text-xs text-muted-foreground">
        <Server className="mr-1 inline size-3 align-[-2px]" />
        Backend: FastAPI on <span className="font-mono text-foreground">127.0.0.1:8000</span> ·
        Interactive API docs at <span className="font-mono text-foreground">/docs</span> ·
        Readiness at <span className="font-mono text-foreground">/v1/health</span>
      </p>
    </div>
  )
}

function Section({
  icon,
  title,
  description,
  children,
}: {
  icon: ReactNode
  title: string
  description?: string
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="flex size-6 items-center justify-center rounded-md border border-border bg-muted/60 text-primary">
            {icon}
          </span>
          {title}
        </h3>
        {description && (
          <p className="max-w-3xl pl-8 text-xs leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {children}
    </section>
  )
}

function Pipeline({
  tone,
  stepIcon,
  heading,
  caption,
  steps,
}: {
  tone: 'blue' | 'violet'
  stepIcon: ReactNode
  heading: string
  caption: string
  steps: { icon: ReactNode; title: string; text: string }[]
}) {
  return (
    <Card className="bg-card/60">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <span
            className={cn(
              'flex size-6 items-center justify-center rounded-md border',
              tone === 'blue'
                ? 'border-primary/30 bg-primary/10 text-primary'
                : 'border-violet-500/30 bg-violet-500/10 text-violet-400',
            )}
          >
            {stepIcon}
          </span>
          {heading}
        </CardTitle>
        <CardDescription className="font-mono text-xs">{caption}</CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="relative flex flex-col gap-3 border-l border-border pl-4">
          {steps.map((step, i) => (
            <li key={step.title} className="relative">
              <span className="absolute top-1 -left-[23px] flex size-4 items-center justify-center rounded-full border border-border bg-background text-[9px] font-semibold tabular-nums text-muted-foreground">
                {i + 1}
              </span>
              <div className="flex items-center gap-1.5 text-sm font-medium">
                <span className="text-primary">{step.icon}</span>
                {step.title}
              </div>
              <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{step.text}</p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  )
}

function Feature({
  icon,
  title,
  text,
}: {
  icon: ReactNode
  title: string
  text: string
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-border bg-card/50 p-3.5">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{text}</p>
    </div>
  )
}

function LayerRow({ name, role, text }: { name: string; role: string; text: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-card/50 p-3 sm:flex-row sm:gap-4">
      <div className="flex shrink-0 items-center gap-2 sm:w-52">
        <code className="rounded bg-muted/70 px-1.5 py-0.5 text-xs text-primary">{name}</code>
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{role}</span>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{text}</p>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-background/60 px-2.5 py-1.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="truncate text-xs font-medium" title={value}>
        {value}
      </dd>
    </div>
  )
}
