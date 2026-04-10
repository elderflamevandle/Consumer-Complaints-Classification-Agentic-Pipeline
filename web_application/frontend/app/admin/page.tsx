'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Users, Shield, Layers, Plus, Pencil, X, Check } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import { useAuthStore } from '@/store/auth'
import { adminApi } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'
import type { Team, User, AuditEvent } from '@/types'

type Tab = 'users' | 'teams' | 'audit'

// ── Issue type options (mirrors mock_pipeline._TEAM_MAP keys) ────────────────
const ISSUE_TYPES = [
  'FRAUD', 'BILLING', 'IDENTITY_THEFT',
  'PAYMENT', 'CREDIT_REPORTING', 'CUSTOMER_SERVICE',
]
const PRODUCT_TYPES = [
  'CREDIT_CARD', 'MORTGAGE', 'LOAN',
  'BANK_ACCOUNT', 'DEBT_COLLECTION', 'MONEY_TRANSFER',
]

// ── Helper to generate a slug from a name ────────────────────────────────────
function toSlug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

export default function AdminPage() {
  const router = useRouter()
  const { user, isAuthenticated, loadUser } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [teams, setTeams] = useState<Team[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('users')
  const [error, setError] = useState<string | null>(null)

  // ── Team form state ─────────────────────────────────────────────────────────
  const [showTeamForm, setShowTeamForm] = useState(false)
  const [teamFormMode, setTeamFormMode] = useState<'create' | 'edit'>('create')
  const [editingTeamId, setEditingTeamId] = useState<string | null>(null)
  const [teamName, setTeamName] = useState('')
  const [teamSlug, setTeamSlug] = useState('')
  const [teamDesc, setTeamDesc] = useState('')
  const [teamIssueTypes, setTeamIssueTypes] = useState<string[]>([])
  const [teamProductTypes, setTeamProductTypes] = useState<string[]>([])
  const [teamFormError, setTeamFormError] = useState<string | null>(null)
  const [teamFormLoading, setTeamFormLoading] = useState(false)

  // ── Auth guard ──────────────────────────────────────────────────────────────
  useEffect(() => {
    loadUser().then(() => {
      const s = useAuthStore.getState()
      if (!s.isAuthenticated) { router.push('/login'); return }
      if (s.user?.role !== 'admin') { router.push('/dashboard'); return }
    })
  }, [])

  // ── Load data ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'admin') return
    Promise.all([
      adminApi.users(100),
      adminApi.listTeams(),
      adminApi.systemAudit(50),
    ]).then(([uRes, tRes, aRes]) => {
      setUsers((uRes.data as any).items)
      setTeams((tRes.data as any).items)
      setAuditEvents((aRes.data as any).events)
    }).catch(() => setError('Failed to load admin data'))
      .finally(() => setLoading(false))
  }, [isAuthenticated, user])

  // ── User actions ────────────────────────────────────────────────────────────
  const handleRoleChange = async (userId: string, role: string) => {
    if (!confirm(`Change role to "${role}"?`)) return
    try {
      await adminApi.changeRole(userId, role)
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: role as any } : u))
    } catch {
      setError('Failed to change role')
    }
  }

  const handleToggleActive = async (u: User) => {
    if (!confirm(`${u.is_active ? 'Deactivate' : 'Activate'} ${u.full_name}?`)) return
    try {
      if (u.is_active) await adminApi.deactivate(u.id)
      else await adminApi.activate(u.id)
      setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: !x.is_active } : x))
    } catch {
      setError('Failed to update user status')
    }
  }

  const handleAssignTeam = async (userId: string, teamId: string) => {
    try {
      const res = await adminApi.assignTeam(userId, teamId || null)
      const updated = res.data as User
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, team_id: updated.team_id, team_name: updated.team_name } : u))
    } catch {
      setError('Failed to assign team')
    }
  }

  // ── Team form helpers ───────────────────────────────────────────────────────
  const openCreateTeam = () => {
    setTeamFormMode('create')
    setEditingTeamId(null)
    setTeamName(''); setTeamSlug(''); setTeamDesc('')
    setTeamIssueTypes([]); setTeamProductTypes([])
    setTeamFormError(null)
    setShowTeamForm(true)
  }

  const openEditTeam = (t: Team) => {
    setTeamFormMode('edit')
    setEditingTeamId(t.id)
    setTeamName(t.name); setTeamSlug(t.slug); setTeamDesc(t.description)
    setTeamIssueTypes([...t.issue_types]); setTeamProductTypes([...t.product_types])
    setTeamFormError(null)
    setShowTeamForm(true)
  }

  const handleTeamSubmit = async () => {
    setTeamFormError(null)
    if (!teamName.trim()) { setTeamFormError('Team name is required'); return }
    if (!teamSlug.trim()) { setTeamFormError('Slug is required'); return }
    if (!/^[a-z0-9-]+$/.test(teamSlug)) { setTeamFormError('Slug must be lowercase letters, numbers, and hyphens only'); return }

    setTeamFormLoading(true)
    try {
      if (teamFormMode === 'create') {
        await adminApi.createTeam({
          name: teamName, slug: teamSlug, description: teamDesc,
          issue_types: teamIssueTypes, product_types: teamProductTypes,
        })
      } else if (editingTeamId) {
        await adminApi.updateTeam(editingTeamId, {
          name: teamName, description: teamDesc,
          issue_types: teamIssueTypes, product_types: teamProductTypes,
        })
      }
      // Refresh teams
      const tRes = await adminApi.listTeams()
      setTeams((tRes.data as any).items)
      setShowTeamForm(false)
    } catch (e: any) {
      setTeamFormError(e.response?.data?.detail ?? 'Failed to save team')
    } finally {
      setTeamFormLoading(false)
    }
  }

  const toggleCheckbox = (
    value: string,
    list: string[],
    setter: (v: string[]) => void,
  ) => {
    setter(list.includes(value) ? list.filter((x) => x !== value) : [...list, value])
  }

  if (loading) return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <div className="flex items-center justify-center py-32 text-slate-400">Loading…</div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Admin</h1>
          <p className="text-sm text-slate-500">User management, teams, and system audit log</p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 flex justify-between">
            {error}
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700"><X className="h-4 w-4" /></button>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-1 rounded-xl bg-slate-100 p-1 w-fit">
          {(['users', 'teams', 'audit'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                activeTab === tab ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {tab === 'users' && <Users className="h-4 w-4" />}
              {tab === 'teams' && <Layers className="h-4 w-4" />}
              {tab === 'audit' && <Shield className="h-4 w-4" />}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* ── USERS TAB ─────────────────────────────────────────────────────── */}
        {activeTab === 'users' && (
          <div className="rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Users ({users.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3 text-left">User</th>
                    <th className="px-4 py-3 text-left">Role</th>
                    <th className="px-4 py-3 text-left">Team</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Last Login</th>
                    <th className="px-4 py-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50 transition">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-900">{u.full_name}</p>
                        <p className="text-xs text-slate-400">{u.email}</p>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={u.role}
                          disabled={u.id === user?.id}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs outline-none focus:ring-2 focus:ring-blue-200 disabled:opacity-50"
                        >
                          <option value="admin">Admin</option>
                          <option value="analyst">Analyst</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={u.team_id ?? ''}
                          onChange={(e) => handleAssignTeam(u.id, e.target.value)}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs outline-none focus:ring-2 focus:ring-blue-200 max-w-[180px]"
                        >
                          <option value="">— Unassigned —</option>
                          {teams.filter((t) => t.is_active).map((t) => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={u.is_active ? 'success' : 'secondary'}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">{formatDate(u.last_login_at)}</td>
                      <td className="px-4 py-3">
                        {u.id !== user?.id && (
                          <button
                            onClick={() => handleToggleActive(u)}
                            className="text-xs font-medium text-blue-600 hover:underline"
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

        {/* ── TEAMS TAB ─────────────────────────────────────────────────────── */}
        {activeTab === 'teams' && (
          <div className="space-y-4">
            <div className="rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">
              <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-slate-900">Teams ({teams.length})</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Complaints are auto-routed to teams based on their issue types
                  </p>
                </div>
                <button
                  onClick={openCreateTeam}
                  className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 transition"
                >
                  <Plus className="h-3.5 w-3.5" /> New Team
                </button>
              </div>

              {/* Team form modal inline */}
              {showTeamForm && (
                <div className="border-b border-slate-100 bg-slate-50 px-6 py-5">
                  <h3 className="text-sm font-semibold text-slate-800 mb-4">
                    {teamFormMode === 'create' ? 'Create Team' : 'Edit Team'}
                  </h3>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">Team Name *</label>
                      <input
                        value={teamName}
                        onChange={(e) => {
                          setTeamName(e.target.value)
                          if (teamFormMode === 'create') setTeamSlug(toSlug(e.target.value))
                        }}
                        placeholder="e.g. Fraud & Security Operations"
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-1">
                        Slug *
                        <span className="ml-1 font-normal text-slate-400">(lowercase, hyphens only — used for auto-routing)</span>
                      </label>
                      <input
                        value={teamSlug}
                        onChange={(e) => setTeamSlug(e.target.value)}
                        disabled={teamFormMode === 'edit'}
                        placeholder="e.g. fraud-security"
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:bg-slate-100 disabled:text-slate-400"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-medium text-slate-600 mb-1">Description</label>
                      <input
                        value={teamDesc}
                        onChange={(e) => setTeamDesc(e.target.value)}
                        placeholder="Brief description of this team's responsibilities"
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                      />
                    </div>

                    {/* Issue types */}
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-2">
                        Issue Types (auto-routing)
                        <span className="ml-1 font-normal text-slate-400">— pipeline routes complaints to this team</span>
                      </label>
                      <div className="grid grid-cols-2 gap-1.5">
                        {ISSUE_TYPES.map((it) => (
                          <label key={it} className="flex items-center gap-2 cursor-pointer text-xs">
                            <input
                              type="checkbox"
                              checked={teamIssueTypes.includes(it)}
                              onChange={() => toggleCheckbox(it, teamIssueTypes, setTeamIssueTypes)}
                              className="rounded border-slate-300"
                            />
                            <span className="text-slate-700">{it.replace(/_/g, ' ')}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Product types */}
                    <div>
                      <label className="block text-xs font-medium text-slate-600 mb-2">Product Types (informational)</label>
                      <div className="grid grid-cols-2 gap-1.5">
                        {PRODUCT_TYPES.map((pt) => (
                          <label key={pt} className="flex items-center gap-2 cursor-pointer text-xs">
                            <input
                              type="checkbox"
                              checked={teamProductTypes.includes(pt)}
                              onChange={() => toggleCheckbox(pt, teamProductTypes, setTeamProductTypes)}
                              className="rounded border-slate-300"
                            />
                            <span className="text-slate-700">{pt.replace(/_/g, ' ')}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {teamFormError && (
                    <p className="mt-3 text-xs text-red-600">{teamFormError}</p>
                  )}

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={handleTeamSubmit}
                      disabled={teamFormLoading}
                      className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50 transition"
                    >
                      <Check className="h-3.5 w-3.5" />
                      {teamFormLoading ? 'Saving…' : teamFormMode === 'create' ? 'Create Team' : 'Save Changes'}
                    </button>
                    <button
                      onClick={() => setShowTeamForm(false)}
                      className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 transition"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Team list */}
              <div className="divide-y divide-slate-50">
                {teams.length === 0 && (
                  <div className="px-6 py-8 text-center text-sm text-slate-400">
                    No teams yet. Click "New Team" to create one.
                  </div>
                )}
                {teams.map((t) => (
                  <div key={t.id} className="px-6 py-4 flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-slate-900 text-sm">{t.name}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-mono text-slate-500">
                          {t.slug}
                        </span>
                        {!t.is_active && (
                          <Badge variant="secondary">Inactive</Badge>
                        )}
                      </div>
                      {t.description && (
                        <p className="mt-0.5 text-xs text-slate-400">{t.description}</p>
                      )}
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {t.issue_types.map((it) => (
                          <span key={it} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                            {it.replace(/_/g, ' ')}
                          </span>
                        ))}
                        {t.issue_types.length === 0 && (
                          <span className="text-xs text-amber-600">⚠ No issue types — auto-routing disabled</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 flex-shrink-0">
                      <div className="text-center">
                        <p className="text-lg font-bold text-slate-900">{t.member_count}</p>
                        <p className="text-xs text-slate-400">members</p>
                      </div>
                      <button
                        onClick={() => openEditTeam(t)}
                        className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 transition"
                      >
                        <Pencil className="h-3.5 w-3.5" /> Edit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Auto-routing reference */}
            <div className="rounded-2xl bg-amber-50 border border-amber-200 px-6 py-4">
              <p className="text-sm font-semibold text-amber-800 mb-1">Auto-routing reference</p>
              <p className="text-xs text-amber-700 mb-3">
                The pipeline automatically routes complaints to teams based on the detected issue type.
                Create teams using the slugs below so complaints are assigned correctly.
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  { issue: 'FRAUD', slug: 'fraud-security' },
                  { issue: 'BILLING', slug: 'billing-resolution' },
                  { issue: 'IDENTITY_THEFT', slug: 'identity-protection' },
                  { issue: 'PAYMENT', slug: 'payments-ops' },
                  { issue: 'CREDIT_REPORTING', slug: 'credit-bureau' },
                  { issue: 'CUSTOMER_SERVICE', slug: 'cx-escalations' },
                ].map(({ issue, slug }) => (
                  <div key={slug} className="rounded-lg bg-white border border-amber-100 px-3 py-2 text-xs">
                    <p className="font-semibold text-slate-700">{issue.replace(/_/g, ' ')}</p>
                    <p className="font-mono text-slate-400">{slug}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── AUDIT TAB ─────────────────────────────────────────────────────── */}
        {activeTab === 'audit' && (
          <div className="rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">System Audit Log</h2>
            </div>
            <div className="divide-y divide-slate-50 text-sm">
              {auditEvents.map((ev) => (
                <div key={ev.id} className="flex items-start gap-4 px-6 py-3">
                  <span className={`mt-0.5 inline-flex rounded-full px-2 py-0.5 text-xs font-medium flex-shrink-0 ${
                    ev.action.startsWith('TEAM_') ? 'bg-purple-100 text-purple-700' :
                    ev.action.startsWith('USER_') ? 'bg-blue-100 text-blue-700' :
                    ev.action.startsWith('PIPELINE_') ? 'bg-green-100 text-green-700' :
                    ev.action.startsWith('COMPLAINT_') ? 'bg-orange-100 text-orange-700' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {ev.action.split('_').slice(0, 2).join('_')}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-700">{ev.action.replace(/_/g, ' ')}</p>
                    {ev.entity_id && (
                      <p className="text-xs text-slate-400">entity: {ev.entity_id.slice(0, 12)}…</p>
                    )}
                  </div>
                  <span className="text-xs text-slate-400 flex-shrink-0 whitespace-nowrap">
                    {formatDate(ev.timestamp)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
