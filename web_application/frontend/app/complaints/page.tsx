'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { FileText, Plus, ArrowUpRight, X } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/auth'
import { teamsApi } from '@/lib/api-client'
import { useComplaintsStore } from '@/store/complaints'
import { formatDate, statusColor, severityColor, cn } from '@/lib/utils'

/* ── Filter options ─────────────────────────────────────────────────────── */
const STATUS_OPTIONS = [
  { label: 'All',             value: '' },
  { label: 'Pending',         value: 'pending' },
  { label: 'Processing',      value: 'processing' },
  { label: 'Awaiting Review', value: 'interrupted' },
  { label: 'Complete',        value: 'complete' },
  { label: 'Rejected',        value: 'rejected' },
  { label: 'Failed',          value: 'failed' },
]

const SEVERITY_OPTIONS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

const SEVERITY_CHIP: Record<string, string> = {
  LOW:      'bg-blue-500/10 text-blue-400 border-blue-500/20',
  MEDIUM:   'bg-amber-500/10 text-amber-400 border-amber-500/20',
  HIGH:     'bg-orange-500/10 text-orange-400 border-orange-500/20',
  CRITICAL: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export default function ComplaintsPage() {
  const router = useRouter()
  const { isAuthenticated, loadUser, user } = useAuthStore()
  const { complaints, total, isLoading, fetchComplaints } = useComplaintsStore()

  // Dynamic team options loaded from DB
  const [teamOptions, setTeamOptions] = useState<{ id: string; name: string; slug: string }[]>([])

  // Filters
  const [statusFilter, setStatusFilter]       = useState('')
  const [severities, setSeverities]           = useState<string[]>([])
  const [teams, setTeams]                     = useState<string[]>([])
  const [page, setPage]                       = useState(0)
  const PAGE_SIZE = 20

  const isAdmin = user?.role === 'admin'
  const hasAdvFilters = severities.length > 0 || teams.length > 0

  const toggleSev = (v: string) => {
    setSeverities((p) => p.includes(v) ? p.filter((x) => x !== v) : [...p, v])
    setPage(0)
  }
  const toggleTeam = (v: string) => {
    setTeams((p) => p.includes(v) ? p.filter((x) => x !== v) : [...p, v])
    setPage(0)
  }
  const clearAll = () => { setSeverities([]); setTeams([]); setPage(0) }

  useEffect(() => {
    if (!isAuthenticated)
      loadUser().then(() => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
  }, [])

  // Fetch teams from DB once authenticated
  useEffect(() => {
    if (!isAuthenticated) return
    teamsApi.list()
      .then((res) => setTeamOptions(res.data.items))
      .catch(() => {/* silently ignore — filters just won't appear */})
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    fetchComplaints({
      status_filter:   statusFilter || undefined,
      severity_filter: severities.length ? severities.join(',') : undefined,
      team_filter:     teams.length ? teams.join(',') : undefined,
      limit: PAGE_SIZE,
      skip: page * PAGE_SIZE,
    })
  }, [isAuthenticated, statusFilter, severities, teams, page])

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
          {/* Only non-admin users can submit new complaints */}
          {!isAdmin && (
            <Link href="/complaints/new" className="btn-primary animate-fade-up">
              <Plus className="h-4 w-4" />
              <span className="hidden sm:block">New</span>
            </Link>
          )}
        </div>

        {/* ── Status filter tabs ───────────────────────────────── */}
        <div className="mb-4 flex flex-wrap gap-1.5 animate-fade-up delay-75">
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

        {/* ── Advanced filters ─────────────────────────────────── */}
        <div className="mb-5 space-y-2.5 animate-fade-up delay-100">
          {/* Severity */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-16 flex-shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
              Severity
            </span>
            {SEVERITY_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => toggleSev(s)}
                className={cn(
                  'rounded-full border px-3 py-1 text-[11px] font-semibold transition-all',
                  severities.includes(s)
                    ? SEVERITY_CHIP[s]
                    : 'border-white/[0.08] bg-white/[0.03] text-muted-foreground/60 hover:border-white/[0.15] hover:text-muted-foreground',
                )}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Team */}
          {teamOptions.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-16 flex-shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">
                Team
              </span>
              {teamOptions.map((t) => (
                <button
                  key={t.slug}
                  onClick={() => toggleTeam(t.slug)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-[11px] font-semibold transition-all',
                    teams.includes(t.slug)
                      ? 'border-violet-500/40 bg-violet-500/15 text-violet-300'
                      : 'border-white/[0.08] bg-white/[0.03] text-muted-foreground/60 hover:border-white/[0.15] hover:text-muted-foreground',
                  )}
                >
                  {t.name}
                </button>
              ))}
            </div>
          )}

          {/* Clear bar */}
          {hasAdvFilters && (
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span>{severities.length + teams.length} filter{severities.length + teams.length > 1 ? 's' : ''} active</span>
              <button
                onClick={clearAll}
                className="flex items-center gap-1 rounded-full border border-white/[0.08] px-2 py-0.5 hover:text-foreground transition-colors"
              >
                <X className="h-2.5 w-2.5" /> Clear all
              </button>
            </div>
          )}
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
                {hasAdvFilters || statusFilter
                  ? 'Try removing some filters'
                  : 'Submit your first complaint to get started'}
              </p>
              {!isAdmin && !statusFilter && !hasAdvFilters && (
                <Link href="/complaints/new" className="btn-primary mt-5 py-2 px-5 text-xs">
                  Submit complaint
                </Link>
              )}
            </div>
          ) : (
            <>
              {/* ── Table header — Complaint | Severity | Status | Team | Created ── */}
              <div className="hidden border-b border-white/[0.06] px-5 py-3 sm:grid sm:grid-cols-[1fr_100px_110px_180px_100px_32px] gap-4">
                {['Complaint', 'Severity', 'Status', 'Team', 'Created', ''].map((h) => (
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
                               grid-cols-1 sm:grid-cols-[1fr_100px_110px_180px_100px_32px]"
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

                    {/* Team (replaces Product) */}
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
