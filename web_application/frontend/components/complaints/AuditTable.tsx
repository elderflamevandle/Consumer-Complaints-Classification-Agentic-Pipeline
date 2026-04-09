'use client'
import { useEffect, useState } from 'react'
import { Shield, ChevronDown, ChevronRight } from 'lucide-react'
import { complaintsApi } from '@/lib/api-client'
import { formatDate } from '@/lib/utils'
import type { AuditEvent } from '@/types'

interface Props { complaintId: string }

export default function AuditTable({ complaintId }: Props) {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    complaintsApi.audit(complaintId).then((res) => {
      setEvents((res.data as any).events ?? [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [complaintId])

  if (loading) return (
    <div className="rounded-2xl bg-white border border-slate-100 shadow-sm p-6 text-sm text-slate-400">
      Loading audit trail…
    </div>
  )

  if (events.length === 0) return (
    <div className="rounded-2xl bg-white border border-slate-100 shadow-sm p-6 text-sm text-slate-400">
      No audit events yet.
    </div>
  )

  return (
    <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 px-6 py-4 flex items-center gap-2">
        <Shield className="h-4 w-4 text-slate-400" />
        <h3 className="font-semibold text-slate-900">Audit Trail</h3>
        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
          {events.length} events
        </span>
      </div>
      <div className="divide-y divide-slate-50 text-sm">
        {events.map((ev) => (
          <div key={ev.id}>
            <button
              className="w-full flex items-center gap-3 px-6 py-3 text-left hover:bg-slate-50 transition"
              onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
            >
              {expanded === ev.id
                ? <ChevronDown className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                : <ChevronRight className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />}
              <span className="flex-1 font-medium text-slate-700">{ev.action.replace(/_/g, ' ')}</span>
              <span className="text-xs text-slate-400 flex-shrink-0">{formatDate(ev.timestamp)}</span>
            </button>
            {expanded === ev.id && Object.keys(ev.details).length > 0 && (
              <div className="px-6 pb-3 pt-1">
                <pre className="rounded-lg bg-slate-50 border border-slate-100 p-3 text-xs text-slate-600 overflow-x-auto">
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
