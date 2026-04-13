/**
 * Zustand complaints store — list cache + active complaint state.
 */
import { create } from 'zustand'
import { complaintsApi } from '@/lib/api-client'
import type { Complaint, PipelineStage, WSMessage } from '@/types'

interface ComplaintsState {
  // List
  complaints: Complaint[]
  total: number
  isLoading: boolean
  listError: string | null
  fetchComplaints: (params?: { status_filter?: string; limit?: number; skip?: number }) => Promise<void>

  // Active (detail view)
  active: Complaint | null
  activeStages: PipelineStage[]
  activeLoading: boolean
  activeError: string | null
  fetchComplaint: (id: string) => Promise<void>
  updateActiveFromWS: (msg: WSMessage) => void
  submitComplaint: (text: string, state_code?: string) => Promise<string>
  submitReview: (id: string, action: string, notes?: string, editedText?: string) => Promise<void>
  clearActive: () => void
}

export const useComplaintsStore = create<ComplaintsState>((set, get) => ({
  complaints: [],
  total: 0,
  isLoading: false,
  listError: null,

  fetchComplaints: async (params) => {
    set({ isLoading: true, listError: null })
    try {
      const res = await complaintsApi.list(params)
      set({ complaints: res.data.items, total: res.data.total, isLoading: false })
    } catch (e: any) {
      set({ listError: e.response?.data?.detail ?? 'Failed to load', isLoading: false })
    }
  },

  active: null,
  activeStages: [],
  activeLoading: false,
  activeError: null,

  fetchComplaint: async (id) => {
    set({ activeLoading: true, activeError: null })
    try {
      const res = await complaintsApi.get(id)
      set({
        active: res.data,
        activeStages: res.data.pipeline_stages ?? [],
        activeLoading: false,
      })
    } catch (e: any) {
      set({ activeError: e.response?.data?.detail ?? 'Not found', activeLoading: false })
    }
  },

  updateActiveFromWS: (msg) => {
    if (msg.type === 'current_state' || msg.type === 'final_state') {
      set({ active: msg.complaint, activeStages: msg.stages })
    } else if (msg.type === 'pipeline_update') {
      // Optimistically update the matching stage
      set((s) => ({
        activeStages: s.activeStages.map((st) =>
          st.node === msg.node
            ? { ...st, status: msg.event === 'started' ? 'running' : msg.event as any }
            : st,
        ),
      }))
    }
  },

  submitComplaint: async (text, state_code = 'CA') => {
    const res = await complaintsApi.submit(text, state_code)
    return res.data.id
  },

  submitReview: async (id, action, notes, editedText) => {
    const res = await complaintsApi.review(id, action, notes, editedText)
    set({ active: res.data })
  },

  clearActive: () => set({ active: null, activeStages: [], activeError: null }),
}))
