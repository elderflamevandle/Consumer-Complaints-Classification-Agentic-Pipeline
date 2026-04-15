/**
 * Zustand auth store — source of truth for session state.
 * Access token is kept in-memory via tokenStore (not persisted).
 */
import { create } from 'zustand'
import { authApi, tokenStore, tryRefresh } from '@/lib/api-client'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name: string) => Promise<void>
  logout: () => Promise<void>
  loadUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const res = await authApi.login(email, password)
      tokenStore.set(res.data.access_token)
      set({ user: res.data.user, isAuthenticated: true, isLoading: false })
    } catch (e: any) {
      set({ error: e.response?.data?.detail ?? 'Login failed', isLoading: false })
      throw e
    }
  },

  register: async (email, password, full_name) => {
    set({ isLoading: true, error: null })
    try {
      const res = await authApi.register(email, password, full_name)
      tokenStore.set(res.data.access_token)
      set({ user: res.data.user, isAuthenticated: true, isLoading: false })
    } catch (e: any) {
      set({ error: e.response?.data?.detail ?? 'Registration failed', isLoading: false })
      throw e
    }
  },

  logout: async () => {
    try { await authApi.logout() } catch { /* ignore */ }
    tokenStore.clear()
    set({ user: null, isAuthenticated: false })
  },

  loadUser: async () => {
    set({ isLoading: true })
    try {
      // If no in-memory token (page refresh / new tab), silently attempt
      // a cookie-based refresh BEFORE calling /me.  This avoids a noisy
      // 401 on /me and lets the interceptor focus on genuine auth failures.
      if (!tokenStore.get()) {
        const tok = await tryRefresh()
        if (!tok) {
          // No valid refresh cookie — user is genuinely unauthenticated.
          set({ user: null, isAuthenticated: false, isLoading: false })
          return
        }
      }
      const res = await authApi.me()
      set({ user: res.data, isAuthenticated: true, isLoading: false })
    } catch {
      tokenStore.clear()
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  clearError: () => set({ error: null }),
}))
