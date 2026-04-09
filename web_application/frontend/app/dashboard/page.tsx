'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { FileText, Users, Clock, AlertTriangle, Plus, TrendingUp } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { adminApi, complaintsApi } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import Navbar from '@/components/layout/Navbar'
import { formatDate, statusColor, severityColor } from '@/lib/utils'
import type { Complaint, DashboardStats } from '@/types'

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export default function DashboardPage() {
  const { user, isAuthenticated, loadUser } = useAuthStore()
  const router = useRouter()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recent, setRecent] = useState<Complaint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) loadUser().then((u) => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
  }, [])

  useEffect(() => {
    if (!isAuthenticated) return
    const load = async () => {
      setLoading(true)
      try {
        const [recentRes] = await Promise.all([
          complaintsApi.list({ limit: 5 }),
        ])
        setRecent(recentRes.data.items)
        if (user?.role === 'admin') {
          const statsRes = await adminApi.stats()
          setStats(statsRes.data)
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [isAuthenticated, user])

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-sm text-slate-500">Welcome back, {user?.full_name}</p>
          </div>
          <Link
            href="/complaints/new"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Complaint
          </Link>
        </div>

        {/* Stat cards */}
        {stats && (
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={<FileText className="h-5 w-5 text-blue-600" />}
              label="Total Complaints"
              value={stats.totals.complaints}
              bg="bg-blue-50"
            />
            <StatCard
              icon={<Clock className="h-5 w-5 text-amber-600" />}
              label="Pending / Processing"
              value={stats.totals.pending}
              bg="bg-amber-50"
            />
            <StatCard
              icon={<AlertTriangle className="h-5 w-5 text-orange-600" />}
              label="Awaiting Review"
              value={stats.totals.interrupted_awaiting_review}
              bg="bg-orange-50"
            />
            <StatCard
              icon={<TrendingUp className="h-5 w-5 text-emerald-600" />}
              label="Last 7 Days"
              value={stats.totals.last_7_days}
              bg="bg-emerald-50"
            />
          </div>
        )}

        {/* Charts row */}
        {stats && (
          <div className="mb-8 grid gap-6 lg:grid-cols-2">
            {/* Daily volume bar chart */}
            <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100">
              <h2 className="mb-4 text-sm font-semibold text-slate-700 uppercase tracking-wide">Daily Volume (7 days)</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={stats.daily_volume}>
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Product type pie */}
            <div className="rounded-2xl bg-white p-6 shadow-sm border border-slate-100">
              <h2 className="mb-4 text-sm font-semibold text-slate-700 uppercase tracking-wide">By Product Type</h2>
              <div className="flex items-center justify-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie data={stats.by_product} dataKey="count" nameKey="product" cx="50%" cy="50%" outerRadius={70}>
                      {stats.by_product.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <ul className="space-y-1.5">
                  {stats.by_product.slice(0, 6).map((p, i) => (
                    <li key={p.product} className="flex items-center gap-2 text-xs text-slate-600">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span>{p.product.replace(/_/g, ' ')}</span>
                      <span className="ml-auto font-semibold text-slate-900">{p.count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Recent complaints */}
        <div className="rounded-2xl bg-white shadow-sm border border-slate-100">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h2 className="font-semibold text-slate-900">Recent Complaints</h2>
            <Link href="/complaints" className="text-sm font-medium text-blue-600 hover:underline">
              View all →
            </Link>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12 text-slate-400">Loading…</div>
          ) : recent.length === 0 ? (
            <div className="flex flex-col items-center py-12 text-slate-400">
              <FileText className="mb-2 h-8 w-8 opacity-30" />
              <p className="text-sm">No complaints yet.</p>
              <Link href="/complaints/new" className="mt-3 text-sm font-medium text-blue-600 hover:underline">Submit first complaint →</Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {recent.map((c) => (
                <Link
                  key={c.id}
                  href={`/complaints/${c.id}`}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 transition group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900 group-hover:text-blue-600 transition">
                      {c.scrubbed_text?.slice(0, 80) ?? 'Complaint #' + c.id.slice(0, 8)}…
                    </p>
                    <p className="mt-0.5 text-xs text-slate-400">{formatDate(c.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {c.classification && (
                      <Badge variant={severityColor(c.classification.severity) as any}>
                        {c.classification.severity}
                      </Badge>
                    )}
                    <Badge variant={statusColor(c.status) as any}>
                      {c.status}
                    </Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function StatCard({ icon, label, value, bg }: { icon: React.ReactNode; label: string; value: number; bg: string }) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm border border-slate-100">
      <div className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl ${bg}`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-slate-900">{value.toLocaleString()}</p>
      <p className="mt-0.5 text-sm text-slate-500">{label}</p>
    </div>
  )
}
