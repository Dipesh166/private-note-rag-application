import type { ReactNode } from 'react'

import { cn } from 'cn'
import { Cpu, Database, FileStack, Info, Loader2, MessageSquareText } from 'lucide-react'
import type { HealthOut } from '@/lib/api'

export type AppView = 'chat' | 'about'

interface AppHeaderProps {
  health: HealthOut | null
  backendOnline: boolean
  view: AppView
  onViewChange: (view: AppView) => void
}

export function AppHeader({ health, backendOnline, view, onViewChange }: AppHeaderProps) {
  return (
    <header className="shrink-0 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-3 px-3 lg:px-4">
        <div className="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-violet-600 via-indigo-500 to-blue-500 shadow-md shadow-indigo-500/30 ring-1 ring-white/10">
          <img
            src="/logo.png"
            alt="Private Knowledge Base logo"
            className="size-full scale-125 object-contain"
          />
        </div>

        <div className="min-w-0">
          <h1 className="truncate text-sm leading-tight font-semibold tracking-tight">
            Private Knowledge Base
          </h1>
          <p className="truncate text-xs text-muted-foreground">
            100% local RAG · documents never leave this machine
          </p>
        </div>

        <div className="ml-auto flex items-center gap-1.5">
          {health && (
            <>
              <StatPill icon={<FileStack className="size-3" />} label={`${health.indexed_docs} docs`} />
              <StatPill icon={<Database className="size-3" />} label={`${health.total_chunks} chunks`} />
              <StatPill
                icon={<Cpu className="size-3" />}
                label={health.llm_device}
                className="hidden sm:flex"
              />
              {health.llm && !health.llm_ready && (
                <StatPill
                  icon={<Loader2 className="size-3 animate-spin" />}
                  label="model loading"
                  className="hidden sm:flex"
                />
              )}
            </>
          )}

          <span className="mx-1 hidden h-5 w-px bg-border sm:block" />

          <div
            className={cn(
              'hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs sm:flex',
              backendOnline
                ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                : 'border-destructive/30 bg-destructive/10 text-destructive',
            )}
            title={
              backendOnline
                ? 'FastAPI is answering on port 8000'
                : 'Start it with: uvicorn app.main:app --reload'
            }
          >
            {backendOnline ? (
              <span className="relative flex size-1.5">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500 opacity-75" />
                <span className="relative inline-flex size-1.5 rounded-full bg-emerald-500" />
              </span>
            ) : (
              <Loader2 className="size-3 animate-spin" />
            )}
            {backendOnline ? 'Backend online' : 'Backend offline'}
          </div>

          <nav className="flex items-center gap-0.5 rounded-full border border-border bg-muted/40 p-0.5">
            <NavButton
              active={view === 'chat'}
              label="Chat"
              onClick={() => onViewChange('chat')}
              icon={<MessageSquareText className="size-3.5" />}
            />
            <NavButton
              active={view === 'about'}
              label="About"
              onClick={() => onViewChange('about')}
              icon={<Info className="size-3.5" />}
            />
          </nav>
        </div>
      </div>
    </header>
  )
}

function NavButton({
  active,
  label,
  icon,
  onClick,
}: {
  active: boolean
  label: string
  icon: ReactNode
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'inline-flex h-6 items-center gap-1 rounded-full px-2.5 text-xs font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
        active
          ? 'bg-background text-foreground shadow-sm ring-1 ring-border'
          : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {icon}
      {label}
    </button>
  )
}

function StatPill({
  icon,
  label,
  className,
}: {
  icon: ReactNode
  label: string
  className?: string
}) {
  return (
    <span
      className={cn(
        'hidden h-7 items-center gap-1 rounded-md border border-border bg-muted/50 px-2 text-xs text-muted-foreground',
        className,
      )}
    >
      {icon}
      {label}
    </span>
  )
}
