'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import {
  FileText, Users, Clock, AlertTriangle, Plus, TrendingUp,
  ArrowRight, ArrowUpRight, Activity,
} from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { adminApi, complaintsApi } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import Navbar from '@/components/layout/Navbar'
import { formatDate, statusColor, severityColor } from '@/lib/utils'
import type { Complaint, DashboardStats } from '@/types'

/* ── Chart palette (dark-optimised) ─────────────────────────────────────── */
const PIE_COLORS = ['#6366F1','#10B981','#F59E0B','#F87171','#A78BFA','#38BDF8','#FB923C','#34D399']

/* ── Stat card type ──────────────────────────────────────────────────────── */
interface StatDef {
  icon:    React.ReactNode
  label:   string
  value:   number
  accent:  string
  glow:    string
}

export default function DashboardPage() {
  const { user, isAuthenticated, loadUser } = useAuthStore()
  const router  = useRouter()
  const [stats, setStats]   = useState<DashboardStats | null>(null)
  const [recent, setRecent] = useState<Complaint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated)
      loadUser().then(() => {
        if (!useAuthStore.getState().isAuthenticated) router.push('/login')
      })
  }, [])

  useEffect(() => {
    if (!isAuthenticated) return
    const load = async () => {
      setLoading(true)
      try {
        const [recentRes] = await Promise.all([complaintsApi.list({ limit: 6 })])
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

  const statDefs: StatDef[] = stats ? [
    {
      icon:   <FileText className="h-4 w-4" />,
      label:  'Total Complaints',
      value:  stats.totals.complaints,
      accent: 'border-primary/30 bg-primary/8',
      glow:   'shadow-glow-indigo-sm',
    },
    {
      icon:   <Clock className="h-4 w-4" />,
      label:  'Pending / Processing',
      value:  stats.totals.pending,
      accent: 'border-amber-500/30 bg-amber-500/8',
      glow:   'shadow-glow-amber',
    },
    {
      icon:   <AlertTriangle className="h-4 w-4" />,
      label:  'Awaiting Review',
      value:  stats.totals.interrupted_awaiting_review,
      accent: 'border-orange-500/30 bg-orange-500/8',
      glow:   '',
    },
    {
      icon:   <TrendingUp className="h-4 w-4" />,
      label:  'Last 7 Days',
      value:  stats.totals.last_7_days,
      accent: 'border-emerald-500/30 bg-emerald-500/8',
      glow:   'shadow-glow-emerald',
    },
  ] : []

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

        {/* ── Page header ─────────────────────────────────────── */}
        <div className="mb-8 flex items-start justify-between gap-4">
          <div className="animate-fade-up">
            <p className="section-label mb-1.5">Welcome back</p>
            <h1 className="font-serif text-3xl text-foreground">{user?.full_name}</h1>
            {user?.team_name && (
              <p className="mt-1 text-sm text-muted-foreground">{user.team_name} &nbsp;·&nbsp; <span className="uppercase text-[10px] tracking-wider">{user.role}</span></p>
            )}
          </div>
          <Link href="/complaints/new" className="btn-primary animate-fade-up flex-shrink-0">
            <Plus className="h-4 w-4" />
            <span className="hidden sm:block">New Complaint</span>
          </Link>
        </div>

        {/* ── Stat cards ──────────────────────────────────────── */}
        {stats && (
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {statDefs.map((s, i) => (
              <StatCard key={i} {...s} delay={i * 75} />
            ))}
          </div>
        )}

        {/* ── Charts row ──────────────────────────────────────── */}
        {stats && (
          <div className="mb-8 grid gap-5 lg:grid-cols-2">

            {/* Daily volume */}
            <div className="glass-card p-5 animate-fade-up delay-300">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="section-label mb-1">Daily Volume</p>
                  <p className="text-xs text-muted-foreground">Complaints over last 7 days</p>
                </div>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={stats.daily_volume} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v: string) => v.slice(5)}
                    tick={{ fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    contentStyle={{ background: 'transparent', border: 'none' }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36}>
                    {stats.daily_volume.map((_, i) => (
                      <Cell
                        key={i}
                        fill={`rgba(99,102,241,${0.4 + (i / stats.daily_volume.length) * 0.5})`}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* By product type */}
            <div className="glass-card p-5 animate-fade-up delay-400">
              <div className="mb-4">
                <p className="section-label mb-1">By Product Type</p>
                <p className="text-xs text-muted-foreground">Distribution of classified complaints</p>
              </div>
              {stats.by_product.length === 0 ? (
                <div className="flex h-[180px] items-center justify-center text-xs text-muted-foreground">
                  No classified complaints yet
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  <ResponsiveContainer width={160} height={160}>
                    <PieChart>
                      <Pie
                        data={stats.by_product}
                        dataKey="count"
                        nameKey="product"
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={72}
                        strokeWidth={0}
                      >
                        {stats.by_product.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ background: 'transparent', border: 'none' }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <ul className="flex-1 space-y-1.5 min-w-0">
                    {stats.by_product.slice(0, 6).map((p, i) => (
                      <li key={p.product ?? `unknown-${i}`} className="flex items-center gap-2 text-xs min-w-0">
                        <span
                          className="h-2 w-2 flex-shrink-0 rounded-full"
                          style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                        />
                        <span className="truncate text-muted-foreground">
                          {(p.product ?? 'Unknown').replace(/_/g, ' ')}
                        </span>
                        <span className="ml-auto font-mono font-semibold text-foreground flex-shrink-0">{p.count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Recent complaints ────────────────────────────────── */}
        <div className="glass-card overflow-hidden animate-fade-up delay-500">
          <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Recent Complaints</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Latest activity in your queue</p>
            </div>
            <Link href="/complaints"
              className="flex items-center gap-1 text-xs font-medium text-primary hover:text-indigo-300 transition-colors">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {loading ? (
            <div className="space-y-0 divide-y divide-white/[0.04]">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-5 py-4">
                  <div className="skeleton h-3 flex-1 rounded" />
                  <div className="skeleton h-5 w-16 rounded-full" />
                </div>
              ))}
            </div>
          ) : recent.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/[0.04] border border-white/[0.06]">
                <FileText className="h-6 w-6 text-muted-foreground/40" />
              </div>
              <p className="text-sm font-medium text-foreground/60">No complaints yet</p>
              <p className="mt-1 text-xs text-muted-foreground">Submit your first complaint to get started</p>
              <Link href="/complaints/new" className="btn-primary mt-5 py-2 px-5 text-xs">
                Submit complaint
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {recent.map((c) => (
                <Link
                  key={c.id}
                  href={`/complaints/${c.id}`}
                  className="group flex items-center gap-4 px-5 py-4 hover:bg-white/[0.03] transition-colors"
                >
                  {/* Status indicator dot */}
                  <div className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                    c.status === 'complete'     ? 'bg-emerald-400' :
                    c.status === 'interrupted'  ? 'bg-amber-400' :
                    c.status === 'processing'   ? 'bg-primary animate-pulse' :
                    c.status === 'failed'       ? 'bg-red-400' : 'bg-white/20'
                  }`} />

                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm text-foreground/90 group-hover:text-foreground transition-colors font-medium">
                      {c.scrubbed_text?.slice(0, 90) ?? `Complaint #${c.id.slice(0, 8)}`}
                      {(c.scrubbed_text?.length ?? 0) > 90 ? '…' : ''}
                    </p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                      {c.id.slice(0, 12)} · {formatDate(c.created_at)}
                      {c.assigned_team ? ` · ${c.assigned_team}` : ''}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {c.classification && (
                      <Badge variant={severityColor(c.classification.severity) as any}>
                        {c.classification.severity}
                      </Badge>
                    )}
                    <Badge variant={statusColor(c.status) as any}>{c.status}</Badge>
                    <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
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

/* ── StatCard ─────────────────────────────────────────────────────────────── */
function StatCard({ icon, label, value, accent, glow, delay }: StatDef & { delay: number }) {
  return (
    <div
      className={`glass-card p-5 border ${accent} ${glow} animate-fade-up transition-all duration-300 hover:-translate-y-0.5`}
      style={{ animationDelay: `${delay}ms`, animationFillMode: 'both' }}
    >
      <div className={`mb-3 inline-flex h-8 w-8 items-center justify-center rounded-lg ${accent}`}>
        <span className="text-foreground/70">{icon}</span>
      </div>
      <p className="font-serif text-3xl text-foreground">{value.toLocaleString()}</p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </div>
  )
}
