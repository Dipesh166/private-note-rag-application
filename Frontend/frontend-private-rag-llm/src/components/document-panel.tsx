import { useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, FileText, Loader2, Trash2, Upload } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from 'cn'

import { clearKnowledgeBase, deleteDocument, uploadDocument } from '@/lib/api'
import type { DocumentOut, UploadResponse } from '@/lib/api'

const ACCEPTED = '.pdf,.md,.txt'

interface DocumentPanelProps {
  documents: DocumentOut[]
  loading: boolean
  onRefresh: () => void
}

export function DocumentPanel({ documents, loading, onRefresh }: DocumentPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [clearing, setClearing] = useState(false)

  async function handleFiles(files: FileList | null) {
    const file = files?.[0]
    if (!file) return

    if (!ACCEPTED.split(',').includes('.' + file.name.split('.').pop()?.toLowerCase())) {
      setNotice({ kind: 'error', text: `"${file.name}" is not a .pdf, .md or .txt file.` })
      return
    }

    setUploading(true)
    setNotice(null)
    try {
      const res: UploadResponse = await uploadDocument(file)
      setNotice({
        kind: res.duplicate ? 'error' : 'ok',
        text: res.duplicate
          ? `"${res.filename}" is already indexed: skipped (SHA-256 match).`
          : `"${res.filename}" accepted, indexing in the background…`,
      })
      onRefresh()
    } catch (err) {
      setNotice({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Upload failed.',
      })
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleDelete(docId: string) {
    try {
      await deleteDocument(docId)
      onRefresh()
    } catch (err) {
      setNotice({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Delete failed.',
      })
    }
  }

  async function handleClearAll() {
    setClearing(true)
    try {
      const res = await clearKnowledgeBase()
      setNotice({ kind: 'ok', text: res.detail })
      onRefresh()
    } catch (err) {
      setNotice({
        kind: 'error',
        text: err instanceof Error ? err.message : 'Could not clear the knowledge base.',
      })
    } finally {
      setClearing(false)
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col gap-2.5">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          Documents
          <span className="rounded-full border border-border bg-muted/60 px-1.5 py-px text-xs font-medium tabular-nums text-muted-foreground">
            {documents.length}
          </span>
        </h2>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="ghost" size="xs" className="text-muted-foreground hover:text-destructive">
              <Trash2 className="size-3.5" />
              Clear all
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Clear the entire knowledge base?</DialogTitle>
              <DialogDescription>
                This deletes every indexed document and all vectors from Chroma. Uploaded
                files are removed too. This cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button variant="destructive" onClick={handleClearAll} disabled={clearing}>
                {clearing && <Loader2 className="size-3.5 animate-spin" />}
                Yes, clear everything
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        className={cn(
          'group flex cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-border bg-muted/25 px-4 py-5 text-center transition-colors hover:border-primary/50 hover:bg-primary/[0.05] focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none',
          dragging && 'border-primary bg-primary/10',
        )}
      >
        <div className="flex size-8 items-center justify-center rounded-lg border border-border bg-background text-muted-foreground transition-colors group-hover:border-primary/30 group-hover:text-primary">
          {uploading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Upload className="size-4" />
          )}
        </div>
        <p className="mt-1 text-sm font-medium">
          {uploading ? 'Uploading…' : 'Drop a file here, or click to browse'}
        </p>
        <p className="text-xs text-muted-foreground">
          PDF, Markdown or TXT · max {20} MB
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {notice && (
        <Alert variant={notice.kind === 'error' ? 'destructive' : 'default'}>
          {notice.kind === 'error' ? (
            <AlertCircle className="size-4" />
          ) : (
            <CheckCircle2 className="size-4 text-emerald-500" />
          )}
          <AlertTitle className="text-xs font-medium">
            {notice.kind === 'error' ? 'Notice' : 'Done'}
          </AlertTitle>
          <AlertDescription className="text-xs">{notice.text}</AlertDescription>
        </Alert>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-xl border border-border bg-card/50">
        <div className="flex flex-col gap-1.5 p-1.5">
          {loading && documents.length === 0
            ? Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))
            : documents.map((doc) => <DocumentRow key={doc.doc_id} doc={doc} onDelete={handleDelete} />)}

          {!loading && documents.length === 0 && (
            <div className="flex flex-col items-center gap-1 py-10 text-center">
              <FileText className="size-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No documents yet</p>
              <p className="max-w-[16rem] text-xs text-muted-foreground/70">
                The bundled project plan is seeded on first backend startup.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: DocumentOut
  onDelete: (docId: string) => void
}) {
  const [deleting, setDeleting] = useState(false)

  return (
    <div className="group flex items-start gap-2.5 rounded-lg border border-transparent p-2 transition-colors hover:border-border hover:bg-muted/50">
      <div
        className={cn(
          'mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border',
          doc.status === 'ready' && 'border-border bg-background text-muted-foreground',
          doc.status === 'processing' && 'border-primary/30 bg-primary/10 text-primary',
          doc.status === 'failed' && 'border-destructive/30 bg-destructive/10 text-destructive',
        )}
      >
        {doc.status === 'processing' ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <FileText className="size-4" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium" title={doc.filename}>
            {doc.filename}
          </p>
          <StatusBadge status={doc.status} />
        </div>

        <p
          className={cn(
            'mt-0.5 line-clamp-2 text-xs',
            doc.status === 'failed' ? 'text-destructive' : 'text-muted-foreground',
          )}
          title={doc.status === 'failed' ? (doc.error ?? '') : undefined}
        >
          {doc.status === 'ready' &&
            `${doc.pages} page${doc.pages === 1 ? '' : 's'} · ${doc.chunks} chunks`}
          {doc.status === 'processing' && 'Indexing…'}
          {doc.status === 'failed' && (doc.error ?? 'Indexing failed')}
        </p>
      </div>

      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={`Delete ${doc.filename}`}
        title={`Delete ${doc.filename}`}
        disabled={deleting}
        className="text-muted-foreground opacity-70 transition-opacity hover:text-destructive group-hover:opacity-100"
        onClick={async () => {
          setDeleting(true)
          await onDelete(doc.doc_id)
          setDeleting(false)
        }}
      >
        {deleting ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
      </Button>
    </div>
  )
}

function StatusBadge({ status }: { status: DocumentOut['status'] }) {
  if (status === 'ready') {
    return (
      <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
        <span className="size-1.5 rounded-full bg-emerald-500" />
        ready
      </span>
    )
  }
  if (status === 'processing') {
    return (
      <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs text-primary">
        <Loader2 className="size-3 animate-spin" />
        indexing
      </span>
    )
  }
  return (
    <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-xs text-destructive">
      <span className="size-1.5 rounded-full bg-destructive" />
      failed
    </span>
  )
}
