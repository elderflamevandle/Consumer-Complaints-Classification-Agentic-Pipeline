/**
 * useComplaint — WebSocket-driven complaint tracker hook.
 * Connects to ws://.../api/complaints/ws/{id} and pipes messages
 * into the Zustand complaints store.
 */
'use client'
import { useEffect, useRef } from 'react'
import { useComplaintsStore } from '@/store/complaints'
import type { WSMessage } from '@/types'

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  .replace(/^http/, 'ws')

export function useComplaintWS(complaintId: string | null) {
  const updateFromWS = useComplaintsStore((s) => s.updateActiveFromWS)
  const fetchComplaint = useComplaintsStore((s) => s.fetchComplaint)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!complaintId) return

    const ws = new WebSocket(`${WS_BASE}/api/complaints/ws/${complaintId}`)
    wsRef.current = ws

    ws.onmessage = (ev) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data)
        if (msg.type !== 'ping') updateFromWS(msg)
        if (msg.type === 'pipeline_done') {
          // Final state fetch to ensure DB-persisted data is shown
          fetchComplaint(complaintId)
        }
      } catch {}
    }

    ws.onerror = () => { /* silent — UI shows stale data */ }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [complaintId])

  return wsRef
}

export function useComplaintDetail(id: string) {
  const { active, activeStages, activeLoading, activeError, fetchComplaint, clearActive } =
    useComplaintsStore()

  useComplaintWS(id)

  useEffect(() => {
    fetchComplaint(id)
    return clearActive
  }, [id])

  return { complaint: active, stages: activeStages, isLoading: activeLoading, error: activeError }
}
