'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Users, Shield, RefreshCw, Loader2 } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import { useAuthStore } from '@/store/auth'
import { adminApi } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/utils'
import type { User, AuditEvent } from '@/types'

export default function AdminPage() {
  const router = useRouter()
  const { user, isAuthenticated, loadUser } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'users' | 'audit'>('users')

  useEffect(() => {
    loadUser().then(() => {
      const s = useAuthStore.getState()
      if (!s.isAuthenticated) { router.push('/login'); return }
      if (s.user?.role !== 'admin') { router.push('/dashboard'); return }
    })
  }, [])

  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'admin') return
    Promise.all([
      adminApi.users(100),
      adminApi.systemAudit(50),
    ]).then(([uRes, aRes]) => {
      setUsers((uRes.data as any).items)
      setAuditEvents((aRes.data as any).events)
    }).finally(() => setLoading(false))
  }, [isAuthenticated, user])

  const handleRoleChange = async (userId: string, role: string) => {
    await adminApi.changeRole(userId, role)
    setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: role as any } : u))
  }

  const handleToggleActive = async (u: User) => {
    if (u.is_active) await adminApi.deactivate(u.id)
    else await adminApi.activate(u.id)
    setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, is_active: !x.is_active } : x))
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
          <p className="text-sm text-slate-500">User management and system audit log</p>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex gap-1 rounded-xl bg-slate-100 p-1 w-fit">
          {(['users', 'audit'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                activeTab === tab ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {tab === 'users' ? <Users className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {activeTab === 'users' && (
          <div className="rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Users ({users.length})</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">User</th>
                  <th className="px-4 py-3 text-left">Role</th>
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
        )}

        {activeTab === 'audit' && (
          <div className="rounded-2xl bg-white shadow-sm border border-slate-100 overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-900">System Audit Log</h2>
            </div>
            <div className="divide-y divide-slate-50 text-sm">
              {auditEvents.map((ev) => (
                <div key={ev.id} className="flex items-start gap-4 px-6 py-3">
                  <span className="mt-0.5 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 flex-shrink-0">
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
