import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  Bot,
  Check,
  ChevronRight,
  Copy,
  FileText,
  Loader2,
  Send,
  Sparkles,
  User,
} from 'lucide-react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { SourceDialog } from '@/components/source-dialog'
import { renderMarkdown } from '@/lib/markdown'
import { cn } from 'cn'

import { chat } from '@/lib/api'
import type { DocumentOut, Source } from '@/lib/api'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  retrievalMs?: number
  error?: boolean
}

const SUGGESTIONS = [
  'What embedding model does this project use?',
  'How are documents chunked before indexing?',
  'What happens when the same file is uploaded twice?',
]

let nextId = 0

interface ChatPanelProps {
  documents: DocumentOut[]
}

export function ChatPanel({ documents }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [scope, setScope] = useState<Set<string>>(new Set())
  const [reader, setReader] = useState<{ sources: Source[]; index: number } | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const readyDocs = documents.filter((d) => d.status === 'ready')

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  useEffect(() => {
    setScope((prev) => {
      const alive = new Set(readyDocs.map((d) => d.doc_id))
      const next = new Set([...prev].filter((id) => alive.has(id)))
      return next.size === prev.size ? prev : next
    })
  }, [documents, readyDocs])
  async function send(question: string) {
    const trimmed = question.trim()
    if (!trimmed || busy) return

    setInput('')
    setBusy(true)
    setMessages((m) => [...m, { id: nextId++, role: 'user', content: trimmed }])

    try {
      const res = await chat({
        question: trimmed,
        doc_ids: scope.size > 0 ? [...scope] : undefined,
      })
      setMessages((m) => [
        ...m,
        {
          id: nextId++,
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          retrievalMs: res.retrieval_ms,
        },
      ])
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: nextId++,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Something went wrong.',
          error: true,
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  function toggleScope(docId: string) {
    setScope((prev) => {
      const next = new Set(prev)
      if (next.has(docId)) next.delete(docId)
      else next.add(docId)
      return next
    })
  }

  const showEmpty = messages.length === 0 && !busy

  return (
    <section className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold tracking-tight">
          <Sparkles className="size-3.5 text-primary" />
          Ask your documents
        </h2>

        {readyDocs.length > 0 && (
          <div className="flex min-w-0 flex-wrap items-center gap-1">
            <span className="text-xs text-muted-foreground">Search in:</span>
            <button
              type="button"
              onClick={() => setScope(new Set())}
              className={cn(
                'rounded-full border px-2 py-0.5 text-xs transition-colors',
                scope.size === 0
                  ? 'border-primary/40 bg-primary/12 text-primary'
                  : 'border-border text-muted-foreground hover:bg-muted',
              )}
              title="Search across every indexed document"
            >
              All documents
            </button>
            {readyDocs.map((doc) => {
              const active = scope.has(doc.doc_id)
              return (
                <button
                  key={doc.doc_id}
                  type="button"
                  onClick={() => toggleScope(doc.doc_id)}
                  className={cn(
                    'max-w-[10rem] truncate rounded-full border px-2 py-0.5 text-xs transition-colors',
                    active
                      ? 'border-primary/40 bg-primary/12 text-primary'
                      : 'border-border text-muted-foreground hover:bg-muted',
                  )}
                  title={
                    active
                      ? 'Searching only this document · click to remove the filter'
                      : `Search only ${doc.filename}`
                  }
                >
                  {doc.filename}
                </button>
              )
            })}
          </div>
        )}
      </div>

      <Card className="min-h-0 flex-1 gap-0 overflow-hidden rounded-xl py-0">

        <div
          ref={scrollRef}
          className="min-h-0 flex-1 overflow-y-auto overscroll-contain"
        >
          <div className="flex min-h-full flex-col gap-5 p-4">
            {showEmpty && <EmptyState onPick={send} />}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onOpenSource={(i) =>
                  msg.sources && setReader({ sources: msg.sources, index: i })
                }
              />
            ))}

            {busy && <ThinkingIndicator />}

            <div className="h-px shrink-0" />
          </div>
        </div>

        <form
          className="shrink-0 border-t border-border bg-card p-2.5"
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
        >
          <div className="flex items-end gap-2 rounded-xl border border-input bg-background px-2.5 py-2 transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/40">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send(input)
                }
              }}
              placeholder="Ask something about your documents…"
              rows={1}
              aria-label="Your question"
              className="max-h-40 min-h-[34px] flex-1 resize-none border-0 bg-transparent px-0 py-0.5 text-sm shadow-none focus-visible:border-0 focus-visible:ring-0 dark:bg-transparent"
            />
            <Button
              type="submit"
              size="icon"
              className="size-8"
              disabled={busy || !input.trim()}
              aria-label="Send message"
            >
              {busy ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </div>
          <p className="mt-1.5 px-1 text-xs text-muted-foreground/80">
            <kbd className="rounded border border-border bg-muted px-1 py-px font-sans text-[11px]">
              Enter
            </kbd>{' '}
            to send ·{' '}
            <kbd className="rounded border border-border bg-muted px-1 py-px font-sans text-[11px]">
              Shift
            </kbd>
            {' + '}
            <kbd className="rounded border border-border bg-muted px-1 py-px font-sans text-[11px]">
              Enter
            </kbd>{' '}
            for a new line
          </p>
        </form>
      </Card>

      <SourceDialog
        sources={reader?.sources ?? []}
        index={reader?.index ?? null}
        onIndexChange={(i) =>
          setReader((prev) => {
            if (i === null || !prev) return null
            return { ...prev, index: i }
          })
        }
      />
    </section>
  )
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8 text-center">
      <div className="flex size-13 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600 via-indigo-500 to-blue-600 shadow-lg shadow-indigo-500/30 ring-1 ring-white/10">
        <img src="/logo.png" alt="" className="size-full scale-125 object-contain" />
      </div>
      <div>
        <p className="text-sm font-medium">Ask anything about your documents</p>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          Answers come only from what you have indexed. Every claim is cited with
          a filename and a page number you can click open.
        </p>
      </div>
      <div className="mt-1 flex max-w-md flex-wrap justify-center gap-1.5">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/10 hover:text-foreground"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <Avatar role="assistant" />
      <div className="flex items-center gap-2 rounded-xl rounded-tl-sm border border-border bg-muted/50 px-3 py-2.5">
        <span className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="size-1.5 animate-bounce rounded-full bg-primary/70"
              style={{ animationDelay: `${i * 120}ms`, animationDuration: '1s' }}
            />
          ))}
        </span>
        <span className="text-xs text-muted-foreground">
          Retrieving chunks &amp; generating locally (~10–30 s)
        </span>
      </div>
    </div>
  )
}

function Avatar({ role }: { role: 'user' | 'assistant' }) {
  const isUser = role === 'user'
  return (
    <div
      className={cn(
        'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border',
        isUser
          ? 'border-primary/30 bg-primary/15 text-primary'
          : 'border-border bg-muted text-muted-foreground',
      )}
      aria-hidden
    >
      {isUser ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
    </div>
  )
}

function MessageBubble({
  message,
  onOpenSource,
}: {
  message: Message
  onOpenSource: (index: number) => void
}) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <Avatar role={message.role} />

      <div className={cn('min-w-0 max-w-[min(100%,46rem)]', isUser && 'text-right')}>
        {message.error ? (
          <Alert variant="destructive" className="text-left">
            <AlertCircle className="size-4" />
            <AlertDescription className="text-xs">{message.content}</AlertDescription>
          </Alert>
        ) : (
          <div
            className={cn(
              'rounded-2xl px-3.5 py-2.5 text-left text-sm',
              isUser
                ? 'rounded-tr-sm bg-primary text-primary-foreground'
                : 'rounded-tl-sm border border-border bg-card text-foreground',
            )}
          >
            {isUser ? (
              <span className="whitespace-pre-wrap">{message.content}</span>
            ) : (
              <div className="prose-local">{renderMarkdown(message.content)}</div>
            )}
          </div>
        )}

        {!message.error && !isUser && (
          <div className="mt-1.5 flex items-center gap-1.5">
            <button
              type="button"
              onClick={copyAnswer}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {copied ? (
                <>
                  <Check className="size-3 text-emerald-500" /> Copied
                </>
              ) : (
                <>
                  <Copy className="size-3" /> Copy
                </>
              )}
            </button>
            {message.retrievalMs !== undefined && (
              <span className="text-xs text-muted-foreground/70">
                retrieved in {message.retrievalMs} ms
              </span>
            )}
          </div>
        )}

        {!message.error && message.sources && message.sources.length > 0 && (
          <div className="mt-2.5 flex flex-col gap-1.5 text-left">
            <p className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
              Sources
              <span className="text-muted-foreground/60">
                · {message.sources.length} chunk
                {message.sources.length > 1 ? 's' : ''}
              </span>
              <span className="ml-auto text-[11px] font-normal text-muted-foreground/60">
                click a chunk to read it in full
              </span>
            </p>

            {message.sources.map((source, i) => (
              <SourceCard
                key={source.chunk_id}
                source={source}
                n={i + 1}
                onClick={() => onOpenSource(i)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SourceCard({
  source,
  n,
  onClick,
}: {
  source: Source
  n: number
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group w-full rounded-lg border border-border bg-muted/30 p-2.5 text-left transition-colors hover:border-primary/40 hover:bg-primary/[0.06] focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/40 focus-visible:outline-none"
    >
      <div className="flex items-center gap-1.5">
        <span className="flex size-4.5 shrink-0 items-center justify-center rounded border border-border bg-background text-[11px] font-medium text-muted-foreground group-hover:border-primary/30 group-hover:text-primary">
          {n}
        </span>
        <FileText className="size-3 shrink-0 text-muted-foreground" />
        <span className="truncate text-xs font-medium" title={source.filename}>
          {source.filename}
        </span>
        <Badge variant="secondary" className="shrink-0 px-1.5 text-[11px]">
          p. {source.page}
        </Badge>
        <span className="ml-auto shrink-0 text-[11px] tabular-nums text-muted-foreground">
          {source.score.toFixed(2)}
        </span>
      </div>

      <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
        {source.excerpt}
      </p>

      <span className="mt-1 inline-flex items-center gap-0.5 text-xs font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
        Read full chunk
        <ChevronRight className="size-3" />
      </span>
    </button>
  )
}
