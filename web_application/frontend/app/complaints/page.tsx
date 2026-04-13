'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { FileText, Plus, ArrowUpRight } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/auth'
import { useComplaintsStore } from '@/store/complaints'
import { formatDate, statusColor, severityColor } from '@/lib/utils'

/* ── Status filter options ───────────────────────────────────────────────── */
const STATUS_OPTIONS = [
  { label: 'All',             value: '' },
  { label: 'Pending',         value: 'pending' },
  { label: 'Processing',      value: 'processing' },
  { label: 'Awaiting Review', value: 'interrupted' },
  { label: 'Complete',        value: 'complete' },
  { label: 'Rejected',        value: 'rejected' },
  { label: 'Failed',          value: 'failed' },
]

export default function ComplaintsPage() {
  const router = useRouter()
  const { isAuthenticated, loadUser } = useAuthStore()
  const { complaints, total, isLoading, fetchComplaints } = useComplaintsStore()
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    if (!isAuthenticated)
      loadUser().then(() => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
  }, [])

  useEffect(() => {
    if (isAuthenticated)
      fetchComplaints({ status_filter: statusFilter || undefined, limit: PAGE_SIZE, skip: page * PAGE_SIZE })
  }, [isAuthenticated, statusFilter, page])

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

        {/* ── Header ──────────────────────────────────────────── */}
        <div className="mb-6 flex items-center justify-between gap-4">
          <div className="animate-fade-up">
            <h1 className="font-serif text-3xl text-foreground">Complaints</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              {total.toLocaleString()} total complaints in queue
            </p>
          </div>
          <Link href="/complaints/new" className="btn-primary animate-fade-up">
            <Plus className="h-4 w-4" />
            <span className="hidden sm:block">New</span>
          </Link>
        </div>

        {/* ── Status filter tabs ───────────────────────────────── */}
        <div className="mb-5 flex flex-wrap gap-1.5 animate-fade-up delay-75">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setStatusFilter(opt.value); setPage(0) }}
              className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all duration-200 ${
                statusFilter === opt.value
                  ? 'bg-primary text-white shadow-glow-indigo-sm'
                  : 'border border-white/[0.08] bg-white/[0.04] text-muted-foreground hover:border-white/[0.14] hover:text-foreground'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* ── Table ───────────────────────────────────────────── */}
        <div className="glass-card overflow-hidden animate-fade-up delay-150">
          {isLoading ? (
            <div className="space-y-0">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 border-b border-white/[0.04] px-5 py-4">
                  <div className="skeleton h-3 w-1/2 rounded" />
                  <div className="skeleton ml-auto h-5 w-16 rounded-full" />
                  <div className="skeleton h-5 w-12 rounded-full" />
                </div>
              ))}
            </div>
          ) : complaints.length === 0 ? (
            <div className="flex flex-col items-center py-20 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/[0.04] border border-white/[0.06]">
                <FileText className="h-6 w-6 text-muted-foreground/40" />
              </div>
              <p className="text-sm font-medium text-foreground/60">No complaints found</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {statusFilter ? `No complaints with status "${statusFilter}"` : 'Submit your first complaint to get started'}
              </p>
              {!statusFilter && (
                <Link href="/complaints/new" className="btn-primary mt-5 py-2 px-5 text-xs">
                  Submit complaint
                </Link>
              )}
            </div>
          ) : (
            <>
              {/* ── Table header ── */}
              <div className="hidden border-b border-white/[0.06] px-5 py-3 sm:grid sm:grid-cols-[1fr_160px_100px_110px_140px_100px_32px] gap-4">
                {['Complaint', 'Product', 'Severity', 'Status', 'Team', 'Created', ''].map((h) => (
                  <span key={h} className="section-label">{h}</span>
                ))}
              </div>

              {/* ── Rows ── */}
              <div className="divide-y divide-white/[0.04]">
                {complaints.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => router.push(`/complaints/${c.id}`)}
                    className="group grid cursor-pointer items-center gap-4 px-5 py-4 transition-colors hover:bg-white/[0.03]
                               grid-cols-1 sm:grid-cols-[1fr_160px_100px_110px_140px_100px_32px]"
                  >
                    {/* Complaint text + ID */}
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground/90 group-hover:text-foreground transition-colors">
                        {c.scrubbed_text?.slice(0, 70) ?? `#${c.id.slice(0, 8)}`}
                        {(c.scrubbed_text?.length ?? 0) > 70 ? '…' : ''}
                      </p>
                      <p className="mt-0.5 font-mono text-[10px] text-muted-foreground/60">
                        {c.id.slice(0, 12)}
                      </p>
                    </div>

                    {/* Product */}
                    <span className="hidden text-xs text-muted-foreground sm:block truncate">
                      {c.classification?.product_type.replace(/_/g, ' ') ?? '—'}
                    </span>

                    {/* Severity */}
                    <div className="hidden sm:block">
                      {c.classification ? (
                        <Badge variant={severityColor(c.classification.severity) as any}>
                          {c.classification.severity}
                        </Badge>
                      ) : <span className="text-xs text-muted-foreground/40">—</span>}
                    </div>

                    {/* Status */}
                    <div>
                      <Badge variant={statusColor(c.status) as any}>{c.status}</Badge>
                    </div>

                    {/* Team */}
                    <span className="hidden text-xs text-muted-foreground sm:block truncate">
                      {c.assigned_team ?? '—'}
                    </span>

                    {/* Created */}
                    <span className="hidden font-mono text-[10px] text-muted-foreground/60 sm:block whitespace-nowrap">
                      {formatDate(c.created_at)}
                    </span>

                    {/* Arrow */}
                    <ArrowUpRight className="hidden h-3.5 w-3.5 text-muted-foreground/30 group-hover:text-muted-foreground/70 transition-colors sm:block" />
                  </div>
                ))}
              </div>

              {/* ── Pagination ── */}
              <div className="flex items-center justify-between border-t border-white/[0.06] px-5 py-3.5">
                <p className="font-mono text-[11px] text-muted-foreground">
                  {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="btn-outline py-1.5 px-3 text-xs disabled:opacity-30"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={(page + 1) * PAGE_SIZE >= total}
                    className="btn-outline py-1.5 px-3 text-xs disabled:opacity-30"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
