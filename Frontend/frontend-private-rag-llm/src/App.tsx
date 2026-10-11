import { useCallback, useEffect, useRef, useState } from 'react'

import { AboutPanel } from '@/components/about-panel'
import { AppHeader } from '@/components/app-header'
import type { AppView } from '@/components/app-header'
import { ChatPanel } from '@/components/chat-panel'
import { DocumentPanel } from '@/components/document-panel'

import { getHealth, listDocuments } from '@/lib/api'
import type { DocumentOut, HealthOut } from '@/lib/api'

export default function App() {
  const [documents, setDocuments] = useState<DocumentOut[]>([])
  const [health, setHealth] = useState<HealthOut | null>(null)
  const [backendOnline, setBackendOnline] = useState(true)
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [view, setView] = useState<AppView>('chat')
  const mountedRef = useRef(true)

  const refreshDocuments = useCallback(async () => {
    try {
      const res = await listDocuments()
      if (!mountedRef.current) return
      setDocuments(res.documents)
      setBackendOnline(true)
    } catch {
      if (mountedRef.current) setBackendOnline(false)
    } finally {
      if (mountedRef.current) setLoadingDocs(false)
    }
  }, [])

  const refreshHealth = useCallback(async () => {
    try {
      const res = await getHealth()
      if (!mountedRef.current) return
      setHealth(res)
      setBackendOnline(true)
    } catch {
      if (mountedRef.current) {
        setHealth(null)
        setBackendOnline(false)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    void refreshDocuments()
    void refreshHealth()
    const timer = window.setInterval(refreshHealth, 20_000)
    return () => {
      mountedRef.current = false
      window.clearInterval(timer)
    }
  }, [refreshDocuments, refreshHealth])

  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === 'processing')
    const timer = window.setInterval(
      refreshDocuments,
      hasProcessing ? 2_500 : 30_000,
    )
    return () => window.clearInterval(timer)
  }, [documents, refreshDocuments])

  return (
    <div className="flex h-svh flex-col overflow-hidden bg-background text-foreground">
      <AppHeader
        health={health}
        backendOnline={backendOnline}
        view={view}
        onViewChange={setView}
      />

      {view === 'about' ? (
        <main className="mx-auto min-h-0 w-full max-w-[1100px] flex-1 overflow-y-auto overscroll-contain p-3 lg:p-6">
          <AboutPanel health={health} />
        </main>
      ) : (
        <main className="mx-auto grid w-full max-w-[1400px] min-h-0 flex-1 grid-cols-1 gap-3 p-3 lg:grid-cols-[340px_minmax(0,1fr)] lg:gap-4 lg:p-4">

          <div className="flex min-h-0 flex-col max-lg:max-h-[45svh]">
            <DocumentPanel
              documents={documents}
              loading={loadingDocs}
              onRefresh={refreshDocuments}
            />
          </div>

          <div className="flex min-h-0 flex-col max-lg:h-[60svh]">
            <ChatPanel documents={documents} />
          </div>
        </main>
      )}
    </div>
  )
}
