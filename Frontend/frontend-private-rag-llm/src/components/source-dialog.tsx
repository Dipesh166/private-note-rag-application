import { useEffect, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Check,
  Copy,
  FileText,
  Sparkles,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import { renderMarkdown } from '@/lib/markdown'
import type { Source } from '@/lib/api'

interface SourceDialogProps {
  sources: Source[]
  index: number | null
  onIndexChange: (index: number | null) => void
}

export function SourceDialog({ sources, index, onIndexChange }: SourceDialogProps) {
  const open = index !== null && index >= 0 && index < sources.length
  const source = open ? sources[index] : null
  const [copiedFrom, setCopiedFrom] = useState<number | null>(null)
  const copied = copiedFrom !== null && copiedFrom === index

  useEffect(() => {
    if (index === null || !open) return
    const at = index
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowLeft' && at > 0) onIndexChange(at - 1)
      if (e.key === 'ArrowRight' && at < sources.length - 1) onIndexChange(at + 1)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, index, sources.length, onIndexChange])

  async function copyText() {
    if (!source || index === null) return
    try {
      await navigator.clipboard.writeText(source.excerpt)
      const at = index
      setCopiedFrom(at)
      window.setTimeout(() => setCopiedFrom((cur) => (cur === at ? null : cur)), 1600)
    } catch {
      setCopiedFrom(null)
    }
  }

  if (!source || index === null) return null

  const hasPrev = index > 0
  const hasNext = index < sources.length - 1

  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next) onIndexChange(null)
      }}
    >
      <DialogContent className="gap-0 overflow-hidden p-0 sm:max-w-3xl">
        <DialogHeader className="gap-1.5 border-b border-border px-4 py-3.5 pr-12 sm:px-5">
          <DialogTitle className="flex items-center gap-2 text-sm">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/12 text-primary">
              <FileText className="size-3.5" />
            </span>
            <span className="truncate" title={source.filename}>
              {source.filename}
            </span>
            <Badge variant="secondary" className="shrink-0 text-[11px] font-medium">
              page {source.page}
            </Badge>
          </DialogTitle>

          <DialogDescription className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
            <span className="inline-flex items-center gap-1">
              <Sparkles className="size-3" />
              relevance {source.score.toFixed(3)}
            </span>
            <span className="text-muted-foreground/70">·</span>
            <span className="font-mono text-xs">{source.chunk_id}</span>
            {sources.length > 1 && (
              <>
                <span className="text-muted-foreground/70">·</span>
                <span>
                  chunk {index + 1} of {sources.length}
                </span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[min(58svh,540px)] overflow-y-auto overscroll-contain px-4 py-4 sm:px-5 sm:py-5">
          <div className="prose-local text-[15px] leading-[1.7] select-text whitespace-pre-wrap text-foreground/95">
            {renderMarkdown(source.excerpt)}
          </div>
        </div>

        <div className="flex items-center gap-2 border-t border-border bg-muted/40 px-3 py-2.5 sm:px-4">
          <Button variant="outline" size="sm" onClick={copyText} disabled={copied}>
            {copied ? (
              <>
                <Check className="size-3.5 text-emerald-500" />
                Copied
              </>
            ) : (
              <>
                <Copy className="size-3.5" />
                Copy chunk
              </>
            )}
          </Button>

          <div className="ml-auto flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={!hasPrev}
              onClick={() => onIndexChange(index - 1)}
              aria-label="Previous chunk"
              title="Previous chunk (←)"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              disabled={!hasNext}
              onClick={() => onIndexChange(index + 1)}
              aria-label="Next chunk"
              title="Next chunk (→)"
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
