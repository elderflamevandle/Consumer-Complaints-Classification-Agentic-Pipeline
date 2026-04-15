/**
 * Axios API client with:
 *  - automatic access token injection (in-memory, not localStorage)
 *  - transparent token refresh on 401
 *  - CSRF token fetching + X-CSRF-Token header on mutating requests
 *  - DOMPurify sanitisation on all string fields in responses
 */
import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── In-memory token store (NOT localStorage — avoids XSS token theft) ─────────
let _accessToken: string | null = null
let _csrfToken: string | null = null
let _refreshPromise: Promise<string | null> | null = null

export const tokenStore = {
  get: () => _accessToken,
  set: (t: string | null) => { _accessToken = t },
  clear: () => { _accessToken = null },
}

// ── DOMPurify sanitiser (browser-only) ───────────────────────────────────────
function sanitize(v: unknown): unknown {
  if (typeof window === 'undefined') return v   // SSR: no DOM, skip
  if (typeof v === 'string') {
    // Lazy-load DOMPurify to avoid SSR errors
    const DOMPurify = require('dompurify')
    return DOMPurify.sanitize(v)
  }
  if (Array.isArray(v)) return v.map(sanitize)
  if (v && typeof v === 'object') {
    const out: Record<string, unknown> = {}
    for (const [k, val] of Object.entries(v as object)) out[k] = sanitize(val)
    return out
  }
  return v
}

// ── CSRF helpers ──────────────────────────────────────────────────────────────
async function fetchCsrf(): Promise<string> {
  const res = await axios.get<{ csrf_token: string }>(
    `${BASE_URL}/api/auth/csrf-token`,
    { withCredentials: true },
  )
  _csrfToken = res.data.csrf_token
  return _csrfToken
}

export async function ensureCsrf(): Promise<string> {
  return _csrfToken ?? fetchCsrf()
}

// ── Refresh helper ────────────────────────────────────────────────────────────
async function doRefresh(): Promise<string | null> {
  try {
    const res = await axios.post<{ access_token: string }>(
      `${BASE_URL}/api/auth/refresh`,
      {},
      { withCredentials: true },
    )
    _accessToken = res.data.access_token
    return _accessToken
  } catch {
    _accessToken = null
    return null
  }
}

// ── Axios instance ────────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  timeout: 30_000,
})

// Request: inject auth + CSRF headers
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  if (_accessToken) config.headers.Authorization = `Bearer ${_accessToken}`
  const method = (config.method ?? 'get').toUpperCase()
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    config.headers['X-CSRF-Token'] = await ensureCsrf()
  }
  return config
})

// Response: refresh on 401, sanitize body
api.interceptors.response.use(
  (res) => { res.data = sanitize(res.data); return res },
  async (err) => {
    const orig = err.config
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true
      if (!_refreshPromise) _refreshPromise = doRefresh().finally(() => { _refreshPromise = null })
      const tok = await _refreshPromise
      if (tok) { orig.headers.Authorization = `Bearer ${tok}`; return api(orig) }
    }
    return Promise.reject(err)
  },
)

export default api

// ── Typed endpoint helpers ────────────────────────────────────────────────────
import type { AuthTokens, Complaint, DashboardStats, PaginatedResponse, Team, User } from '@/types'

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    api.post<AuthTokens>('/api/auth/register', { email, password, full_name }),
  login: (email: string, password: string) =>
    api.post<AuthTokens>('/api/auth/login', { email, password }),
  logout: () => api.post('/api/auth/logout'),
  me: () => api.get<User>('/api/auth/me'),
}

export const complaintsApi = {
  submit: (complaint_text: string, state_code = 'CA') =>
    api.post<{ id: string; status: string; websocket_url: string }>(
      '/api/complaints', { complaint_text, state_code }),
  list: (params?: {
    status_filter?: string    // comma-separated e.g. "complete,failed"
    product_filter?: string
    severity_filter?: string
    team_filter?: string
    limit?: number
    skip?: number
  }) => api.get<PaginatedResponse<Complaint>>('/api/complaints', { params }),
  get: (id: string) => api.get<Complaint>(`/api/complaints/${id}`),
  review: (id: string, action: string, reviewer_notes?: string, edited_text?: string) =>
    api.post<Complaint>(`/api/complaints/${id}/review`, { action, reviewer_notes, edited_text }),
  assign: (id: string, assigned_team: string) =>
    api.post<Complaint>(`/api/complaints/${id}/assign`, { assigned_team }),
  updateResponse: (id: string, response_draft: string) =>
    api.patch<Complaint>(`/api/complaints/${id}/response`, { response_draft }),
  audit: (id: string) => api.get(`/api/complaints/${id}/audit`),
}

export const adminApi = {
  stats: () => api.get<DashboardStats>('/api/admin/stats'),
  users: (limit = 50, skip = 0) =>
    api.get<PaginatedResponse<User>>('/api/admin/users', { params: { limit, skip } }),
  changeRole: (userId: string, role: string) =>
    api.patch(`/api/admin/users/${userId}/role`, { role }),
  deactivate: (userId: string, reason?: string) =>
    api.patch(`/api/admin/users/${userId}/deactivate`, { reason }),
  activate: (userId: string) => api.patch(`/api/admin/users/${userId}/activate`),
  assignTeam: (userId: string, teamId: string | null) =>
    api.patch<User>(`/api/admin/users/${userId}/team`, { team_id: teamId }),
  systemAudit: (limit = 100, action_filter?: string) =>
    api.get('/api/admin/audit', { params: { limit, action_filter } }),
  // Team CRUD
  listTeams: (includeInactive = false) =>
    api.get<{ items: Team[]; total: number }>('/api/admin/teams', {
      params: { include_inactive: includeInactive },
    }),
  createTeam: (data: {
    name: string; slug: string; description?: string
    issue_types?: string[]; product_types?: string[]
  }) => api.post<{ id: string; name: string; slug: string }>('/api/admin/teams', data),
  updateTeam: (teamId: string, data: Partial<{
    name: string; description: string
    issue_types: string[]; product_types: string[]; is_active: boolean
  }>) => api.patch(`/api/admin/teams/${teamId}`, data),
}

export const teamsApi = {
  myTeam: () => api.get<{ team: Team; members: User[] }>('/api/teams/me'),
  myComplaints: (params?: { status_filter?: string; limit?: number; skip?: number }) =>
    api.get<PaginatedResponse<Complaint>>('/api/teams/me/complaints', { params }),
  myMembers: () => api.get<{ members: User[]; total: number }>('/api/teams/me/members'),
}
