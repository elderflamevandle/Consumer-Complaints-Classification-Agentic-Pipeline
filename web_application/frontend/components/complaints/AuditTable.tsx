'use client'
import { useEffect, useState } from 'react'
import { Shield, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { complaintsApi } from '@/lib/api-client'
import { formatDate } from '@/lib/utils'
import type { AuditEvent } from '@/types'

interface Props { complaintId: string }

export default function AuditTable({ complaintId }: Props) {
  const [events, setEvents]   = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    complaintsApi.audit(complaintId)
      .then((res) => setEvents((res.data as any).events ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [complaintId])

  if (loading) return (
    <div className="glass-card flex items-center gap-3 p-5 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading audit trail…
    </div>
  )

  if (events.length === 0) return (
    <div className="glass-card p-5 text-sm text-muted-foreground text-center py-8">
      No audit events recorded yet.
    </div>
  )

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-3.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
          <Shield className="h-3.5 w-3.5 text-primary" />
        </div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground/70">Audit Trail</h3>
        <span className="ml-auto rounded-full border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
          {events.length} events
        </span>
      </div>

      <div className="divide-y divide-white/[0.04] text-sm">
        {events.map((ev) => (
          <div key={ev.id}>
            <button
              className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-white/[0.03] transition-colors"
              onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
            >
              {expanded === ev.id
                ? <ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground/50" />
                : <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground/30" />
              }
              <span className="flex-1 text-sm text-foreground/75">
                {ev.action.replace(/_/g, ' ')}
              </span>
              <span className="flex-shrink-0 font-mono text-[10px] text-muted-foreground/50 whitespace-nowrap">
                {formatDate(ev.timestamp)}
              </span>
            </button>

            {expanded === ev.id && Object.keys(ev.details).length > 0 && (
              <div className="px-5 pb-3 pt-1">
                <pre className="output-block text-[11px]">
                  {JSON.stringify(ev.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
