'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Users, Shield, Layers, Plus, Pencil, X, Check, Loader2, AlertTriangle } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import { useAuthStore } from '@/store/auth'
import { adminApi } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { Team, User, AuditEvent } from '@/types'

type Tab = 'users' | 'teams' | 'audit'

const ISSUE_TYPES   = ['FRAUD','BILLING','IDENTITY_THEFT','PAYMENT','CREDIT_REPORTING','CUSTOMER_SERVICE']
const PRODUCT_TYPES = ['CREDIT_CARD','MORTGAGE','LOAN','BANK_ACCOUNT','DEBT_COLLECTION','MONEY_TRANSFER']

const ROUTING_REF = [
  { issue: 'FRAUD',           slug: 'fraud-security' },
  { issue: 'BILLING',         slug: 'billing-resolution' },
  { issue: 'IDENTITY_THEFT',  slug: 'identity-protection' },
  { issue: 'PAYMENT',         slug: 'payments-ops' },
  { issue: 'CREDIT_REPORTING',slug: 'credit-bureau' },
  { issue: 'CUSTOMER_SERVICE',slug: 'cx-escalations' },
]

function toSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

const TAB_ICONS = {
  users: <Users className="h-4 w-4" />,
  teams: <Layers className="h-4 w-4" />,
  audit: <Shield className="h-4 w-4" />,
}

export default function AdminPage() {
  const router = useRouter()
  const { user, isAuthenticated, loadUser } = useAuthStore()
  const [users, setUsers]             = useState<User[]>([])
  const [teams, setTeams]             = useState<Team[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading]         = useState(true)
  const [activeTab, setActiveTab]     = useState<Tab>('users')
  const [pageError, setPageError]     = useState<string | null>(null)

  // Team form state
  const [showTeamForm, setShowTeamForm]       = useState(false)
  const [teamFormMode, setTeamFormMode]       = useState<'create' | 'edit'>('create')
  const [editingTeamId, setEditingTeamId]     = useState<string | null>(null)
  const [teamName, setTeamName]               = useState('')
  const [teamSlug, setTeamSlug]               = useState('')
  const [teamDesc, setTeamDesc]               = useState('')
  const [teamIssueTypes, setTeamIssueTypes]   = useState<string[]>([])
  const [teamProductTypes, setTeamProductTypes] = useState<string[]>([])
  const [teamFormError, setTeamFormError]     = useState<string | null>(null)
  const [teamFormLoading, setTeamFormLoading] = useState(false)

  useEffect(() => {
    loadUser().then(() => {
      const s = useAuthStore.getState()
      if (!s.isAuthenticated) { router.push('/login'); return }
      if (s.user?.role !== 'admin') { router.push('/dashboard'); return }
    })
  }, [])

  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'admin') return
    Promise.all([adminApi.users(100), adminApi.listTeams(), adminApi.systemAudit(50)])
      .then(([uRes, tRes, aRes]) => {
        setUsers((uRes.data as any).items)
        setTeams((tRes.data as any).items)
        setAuditEvents((aRes.data as any).events)
      })
      .catch(() => setPageError('Failed to load admin data'))
      .finally(() => setLoading(false))
  }, [isAuthenticated, user])

  const handleRoleChange = async (userId: string, role: string) => {
    if (!confirm(`Change role to "${role}"?`)) return
    try {
      await adminApi.changeRole(userId, role)
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: role as any } : u))
    } catch { setPageError('Failed to change role') }
  }

  const handleToggleActive = async (u: User) => {
    if (!confirm(`${u.is_active ? 'Deactivate' : 'Activate'} ${u.full_name}?`)) return
    try {
      if (u.is_active) await adminApi.deactivate(u.id)
      else await adminApi.activate(u.id)
      setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: !x.is_active } : x))
    } catch { setPageError('Failed to update user') }
  }

  const handleAssignTeam = async (userId: string, teamId: string) => {
    try {
      const res = await adminApi.assignTeam(userId, teamId || null)
      const updated = res.data as User
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, team_id: updated.team_id, team_name: updated.team_name } : u))
    } catch { setPageError('Failed to assign team') }
  }

  const openCreateTeam = () => {
    setTeamFormMode('create'); setEditingTeamId(null)
    setTeamName(''); setTeamSlug(''); setTeamDesc('')
    setTeamIssueTypes([]); setTeamProductTypes([])
    setTeamFormError(null); setShowTeamForm(true)
  }

  const openEditTeam = (t: Team) => {
    setTeamFormMode('edit'); setEditingTeamId(t.id)
    setTeamName(t.name); setTeamSlug(t.slug); setTeamDesc(t.description)
    setTeamIssueTypes([...t.issue_types]); setTeamProductTypes([...t.product_types])
    setTeamFormError(null); setShowTeamForm(true)
  }

  const handleTeamSubmit = async () => {
    setTeamFormError(null)
    if (!teamName.trim()) { setTeamFormError('Team name is required'); return }
    if (!teamSlug.trim()) { setTeamFormError('Slug is required'); return }
    if (!/^[a-z0-9-]+$/.test(teamSlug)) { setTeamFormError('Slug: lowercase, numbers, hyphens only'); return }
    setTeamFormLoading(true)
    try {
      if (teamFormMode === 'create') {
        await adminApi.createTeam({ name: teamName, slug: teamSlug, description: teamDesc, issue_types: teamIssueTypes, product_types: teamProductTypes })
      } else if (editingTeamId) {
        await adminApi.updateTeam(editingTeamId, { name: teamName, description: teamDesc, issue_types: teamIssueTypes, product_types: teamProductTypes })
      }
      const tRes = await adminApi.listTeams()
      setTeams((tRes.data as any).items)
      setShowTeamForm(false)
    } catch (e: any) {
      setTeamFormError(e.response?.data?.detail ?? 'Failed to save team')
    } finally {
      setTeamFormLoading(false)
    }
  }

  const toggleCheckbox = (value: string, list: string[], setter: (v: string[]) => void) => {
    setter(list.includes(value) ? list.filter((x) => x !== value) : [...list, value])
  }

  if (loading) return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="flex items-center justify-center py-32 gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm">Loading admin data…</span>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

        {/* ── Header ────────────────────────────────────────── */}
        <div className="mb-7 animate-fade-up">
          <h1 className="font-serif text-3xl text-foreground">Admin Console</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            User management · Team RBAC · System audit log
          </p>
        </div>

        {/* ── Page error ────────────────────────────────────── */}
        {pageError && (
          <div className="mb-5 flex items-center gap-3 rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span className="flex-1">{pageError}</span>
            <button onClick={() => setPageError(null)}>
              <X className="h-4 w-4 opacity-60 hover:opacity-100" />
            </button>
          </div>
        )}

        {/* ── Tabs ──────────────────────────────────────────── */}
        <div className="mb-6 flex gap-1 rounded-xl border border-white/[0.06] bg-card p-1 w-fit animate-fade-up delay-75">
          {(['users', 'teams', 'audit'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200',
                activeTab === tab
                  ? 'bg-primary/15 text-primary border border-primary/25'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/[0.04]'
              )}
            >
              {TAB_ICONS[tab]}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* ═════════════════════════════════════════════════════
            USERS TAB
            ════════════════════════════════════════════════════ */}
        {activeTab === 'users' && (
          <div className="glass-card overflow-hidden animate-fade-up delay-150">
            <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Users</h2>
                <p className="text-xs text-muted-foreground mt-0.5">{users.length} registered accounts</p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[700px]">
                <thead>
                  <tr className="border-b border-white/[0.04]">
                    {['User', 'Role', 'Team', 'Status', 'Last Login', 'Actions'].map((h) => (
                      <th key={h} className="px-5 py-3 text-left">
                        <span className="section-label">{h}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/15 border border-primary/20">
                            <span className="text-[10px] font-bold text-primary uppercase">
                              {u.full_name.charAt(0)}
                            </span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-foreground">{u.full_name}</p>
                            <p className="font-mono text-[10px] text-muted-foreground">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <select
                          value={u.role}
                          disabled={u.id === user?.id}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          className="field py-1 px-2 text-xs w-28 disabled:opacity-40 bg-card"
                        >
                          <option value="admin">Admin</option>
                          <option value="analyst">Analyst</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      </td>
                      <td className="px-5 py-3.5">
                        <select
                          value={u.team_id ?? ''}
                          onChange={(e) => handleAssignTeam(u.id, e.target.value)}
                          className="field py-1 px-2 text-xs w-44 bg-card"
                        >
                          <option value="">— Unassigned —</option>
                          {teams.filter((t) => t.is_active).map((t) => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={u.is_active ? 'success' : 'secondary'}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-[10px] text-muted-foreground whitespace-nowrap">
                        {formatDate(u.last_login_at)}
                      </td>
                      <td className="px-5 py-3.5">
                        {u.id !== user?.id && (
                          <button
                            onClick={() => handleToggleActive(u)}
                            className={cn(
                              'text-xs font-medium transition-colors',
                              u.is_active ? 'text-red-400 hover:text-red-300' : 'text-emerald-400 hover:text-emerald-300'
                            )}
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════
            TEAMS TAB
            ════════════════════════════════════════════════════ */}
        {activeTab === 'teams' && (
          <div className="space-y-5 animate-fade-up delay-150">

            {/* Team list */}
            <div className="glass-card overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Teams</h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Complaints auto-route to teams based on issue type
                  </p>
                </div>
                <button onClick={openCreateTeam} className="btn-primary py-1.5 px-3 text-xs">
                  <Plus className="h-3.5 w-3.5" /> New Team
                </button>
              </div>

              {/* Inline form */}
              {showTeamForm && (
                <div className="border-b border-white/[0.06] bg-white/[0.02] px-5 py-5">
                  <h3 className="mb-4 text-sm font-semibold text-foreground">
                    {teamFormMode === 'create' ? 'Create New Team' : 'Edit Team'}
                  </h3>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="section-label mb-1.5 block">Team Name *</label>
                      <input
                        value={teamName}
                        onChange={(e) => {
                          setTeamName(e.target.value)
                          if (teamFormMode === 'create') setTeamSlug(toSlug(e.target.value))
                        }}
                        placeholder="e.g. Fraud & Security Operations"
                        className="field text-sm"
                      />
                    </div>
                    <div>
                      <label className="section-label mb-1.5 block">
                        Slug *
                        <span className="ml-1 normal-case font-normal text-muted-foreground/60">— used for auto-routing</span>
                      </label>
                      <input
                        value={teamSlug}
                        onChange={(e) => setTeamSlug(e.target.value)}
                        disabled={teamFormMode === 'edit'}
                        placeholder="e.g. fraud-security"
                        className="field text-sm font-mono disabled:opacity-40"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="section-label mb-1.5 block">Description</label>
                      <input
                        value={teamDesc}
                        onChange={(e) => setTeamDesc(e.target.value)}
                        placeholder="Brief description of this team's scope"
                        className="field text-sm"
                      />
                    </div>

                    {/* Issue types */}
                    <div>
                      <label className="section-label mb-2 block">
                        Issue Types
                        <span className="ml-1 normal-case font-normal text-muted-foreground/60">— auto-routing triggers</span>
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {ISSUE_TYPES.map((it) => (
                          <label key={it} className="flex cursor-pointer items-center gap-2 text-xs">
                            <input
                              type="checkbox"
                              checked={teamIssueTypes.includes(it)}
                              onChange={() => toggleCheckbox(it, teamIssueTypes, setTeamIssueTypes)}
                              className="rounded border-white/20 bg-input checked:bg-primary"
                            />
                            <span className="text-foreground/80">{it.replace(/_/g, ' ')}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Product types */}
                    <div>
                      <label className="section-label mb-2 block">Product Types (informational)</label>
                      <div className="grid grid-cols-2 gap-2">
                        {PRODUCT_TYPES.map((pt) => (
                          <label key={pt} className="flex cursor-pointer items-center gap-2 text-xs">
                            <input
                              type="checkbox"
                              checked={teamProductTypes.includes(pt)}
                              onChange={() => toggleCheckbox(pt, teamProductTypes, setTeamProductTypes)}
                              className="rounded border-white/20 bg-input checked:bg-primary"
                            />
                            <span className="text-foreground/80">{pt.replace(/_/g, ' ')}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {teamFormError && (
                    <p className="mt-3 text-xs text-red-400">{teamFormError}</p>
                  )}

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={handleTeamSubmit}
                      disabled={teamFormLoading}
                      className="btn-primary py-2 px-4 text-xs"
                    >
                      {teamFormLoading ? (
                        <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…</>
                      ) : (
                        <><Check className="h-3.5 w-3.5" />{teamFormMode === 'create' ? 'Create Team' : 'Save Changes'}</>
                      )}
                    </button>
                    <button
                      onClick={() => setShowTeamForm(false)}
                      className="btn-outline py-2 px-4 text-xs"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Teams list */}
              <div className="divide-y divide-white/[0.04]">
                {teams.length === 0 ? (
                  <div className="py-12 text-center">
                    <p className="text-sm text-muted-foreground">No teams yet.</p>
                    <button onClick={openCreateTeam} className="btn-primary mt-4 py-2 px-4 text-xs">
                      Create first team
                    </button>
                  </div>
                ) : (
                  teams.map((t) => (
                    <div key={t.id} className="flex items-start gap-5 px-5 py-4 hover:bg-white/[0.02] transition-colors">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-foreground">{t.name}</span>
                          <span className="rounded-full border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                            {t.slug}
                          </span>
                          {!t.is_active && <Badge variant="secondary">Inactive</Badge>}
                        </div>
                        {t.description && (
                          <p className="text-xs text-muted-foreground mb-2">{t.description}</p>
                        )}
                        <div className="flex flex-wrap gap-1.5">
                          {t.issue_types.length === 0 ? (
                            <span className="text-[11px] text-amber-400/80">⚠ No issue types — auto-routing disabled</span>
                          ) : (
                            t.issue_types.map((it) => (
                              <span key={it} className="rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                                {it.replace(/_/g, ' ')}
                              </span>
                            ))
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 flex-shrink-0">
                        <div className="text-right">
                          <p className="font-serif text-xl text-foreground">{t.member_count}</p>
                          <p className="text-[10px] text-muted-foreground">members</p>
                        </div>
                        <button
                          onClick={() => openEditTeam(t)}
                          className="btn-outline py-1.5 px-3 text-xs"
                        >
                          <Pencil className="h-3 w-3" /> Edit
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Auto-routing reference */}
            <div className="glass-card overflow-hidden">
              <div className="border-b border-white/[0.06] px-5 py-4">
                <h3 className="text-sm font-semibold text-foreground">Auto-routing Reference</h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Create teams using these slugs for the pipeline to route complaints automatically
                </p>
              </div>
              <div className="grid grid-cols-2 gap-0 sm:grid-cols-3 divide-x divide-y divide-white/[0.04]">
                {ROUTING_REF.map(({ issue, slug }) => (
                  <div key={slug} className="px-4 py-3.5">
                    <p className="text-xs font-semibold text-foreground/80">{issue.replace(/_/g, ' ')}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-primary/70">{slug}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════
            AUDIT TAB
            ════════════════════════════════════════════════════ */}
        {activeTab === 'audit' && (
          <div className="glass-card overflow-hidden animate-fade-up delay-150">
            <div className="border-b border-white/[0.06] px-5 py-4">
              <h2 className="text-sm font-semibold text-foreground">System Audit Log</h2>
              <p className="text-xs text-muted-foreground mt-0.5">{auditEvents.length} recent events</p>
            </div>
            <div className="divide-y divide-white/[0.04]">
              {auditEvents.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">No audit events</div>
              ) : auditEvents.map((ev) => {
                const category = ev.action.split('_')[0]
                const COLORS: Record<string, string> = {
                  TEAM:      'bg-violet-500/15 text-violet-400 border-violet-500/25',
                  USER:      'bg-primary/15 text-indigo-400 border-primary/25',
                  PIPELINE:  'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
                  COMPLAINT: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
                }
                return (
                  <div key={ev.id} className="flex items-start gap-4 px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
                    <span className={cn(
                      'mt-0.5 inline-flex flex-shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wide',
                      COLORS[category] ?? 'bg-white/[0.06] text-muted-foreground border-white/10'
                    )}>
                      {category}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground/80">{ev.action.replace(/_/g, ' ')}</p>
                      {ev.entity_id && (
                        <p className="font-mono text-[10px] text-muted-foreground/60">
                          entity: {ev.entity_id.slice(0, 16)}…
                        </p>
                      )}
                    </div>
                    <span className="flex-shrink-0 font-mono text-[10px] text-muted-foreground/50 whitespace-nowrap">
                      {formatDate(ev.timestamp)}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
