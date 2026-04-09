'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { FileText, Plus, Search, Filter } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/auth'
import { useComplaintsStore } from '@/store/complaints'
import { formatDate, statusColor, severityColor } from '@/lib/utils'
import type { ComplaintStatus } from '@/types'

const STATUS_OPTIONS: Array<{ label: string; value: string }> = [
  { label: 'All', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Processing', value: 'processing' },
  { label: 'Awaiting Review', value: 'interrupted' },
  { label: 'Complete', value: 'complete' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'Failed', value: 'failed' },
]

export default function ComplaintsPage() {
  const router = useRouter()
  const { isAuthenticated, loadUser } = useAuthStore()
  const { complaints, total, isLoading, fetchComplaints } = useComplaintsStore()
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    if (!isAuthenticated) loadUser().then(() => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchComplaints({ status_filter: statusFilter || undefined, limit: PAGE_SIZE, skip: page * PAGE_SIZE })
    }
  }, [isAuthenticated, statusFilter, page])

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Complaints</h1>
            <p className="text-sm text-slate-500">{total.toLocaleString()} total</p>
          </div>
          <Link
            href="/complaints/new"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Complaint
          </Link>
        </div>

        {/* Filter tabs */}
        <div className="mb-4 flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setStatusFilter(opt.value); setPage(0) }}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                statusFilter === opt.value
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-20 text-slate-400">Loading…</div>
          ) : complaints.length === 0 ? (
            <div className="flex flex-col items-center py-20 text-slate-400">
              <FileText className="mb-2 h-10 w-10 opacity-30" />
              <p>No complaints found.</p>
            </div>
          ) : (
            <>
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3 text-left">Complaint</th>
                    <th className="px-4 py-3 text-left">Product</th>
                    <th className="px-4 py-3 text-left">Severity</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Team</th>
                    <th className="px-4 py-3 text-left">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {complaints.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => router.push(`/complaints/${c.id}`)}
                      className="cursor-pointer hover:bg-slate-50 transition"
                    >
                      <td className="px-4 py-3 max-w-xs">
                        <p className="truncate font-medium text-slate-900">
                          {c.scrubbed_text?.slice(0, 60) ?? `#${c.id.slice(0, 8)}`}…
                        </p>
                        <p className="text-xs text-slate-400">{c.id.slice(0, 8)}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {c.classification?.product_type.replace(/_/g, ' ') ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        {c.classification ? (
                          <Badge variant={severityColor(c.classification.severity) as any}>
                            {c.classification.severity}
                          </Badge>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={statusColor(c.status) as any}>{c.status}</Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">
                        {c.assigned_team ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                        {formatDate(c.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
                <p className="text-xs text-slate-500">
                  Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 disabled:opacity-40 hover:bg-slate-50 transition"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={(page + 1) * PAGE_SIZE >= total}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 disabled:opacity-40 hover:bg-slate-50 transition"
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
