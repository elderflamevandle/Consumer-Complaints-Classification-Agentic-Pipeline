/**
 * useComplaint — WebSocket-driven complaint tracker hook.
 * Connects to ws://.../api/complaints/ws/{id}?token=<jwt> and pipes
 * messages into the Zustand complaints store.
 */
'use client'
import { useEffect, useRef } from 'react'
import { useComplaintsStore } from '@/store/complaints'
import { tokenStore, tryRefresh } from '@/lib/api-client'
import type { WSMessage } from '@/types'

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
  .replace(/^http/, 'ws')

export function useComplaintWS(complaintId: string | null) {
  const updateFromWS = useComplaintsStore((s) => s.updateActiveFromWS)
  const fetchComplaint = useComplaintsStore((s) => s.fetchComplaint)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!complaintId) return

    let cancelled = false

    async function connect() {
      // Ensure we have a valid JWT — refresh if the in-memory token is gone
      let token = tokenStore.get()
      if (!token) token = await tryRefresh()
      if (!token || cancelled) return

      const ws = new WebSocket(
        `${WS_BASE}/api/complaints/ws/${complaintId}?token=${encodeURIComponent(token)}`
      )
      if (cancelled) { ws.close(); return }
      wsRef.current = ws

      ws.onmessage = (ev) => {
        try {
          const msg: WSMessage = JSON.parse(ev.data)
          if (msg.type !== 'ping') updateFromWS(msg)
          if (msg.type === 'pipeline_done') {
            // Final HTTP fetch to get DB-persisted data (response letter, etc.)
            fetchComplaint(complaintId)
          }
        } catch {}
      }

      ws.onerror = () => {
        // Connection refused or token rejected — fall back to polling
        if (!cancelled) {
          setTimeout(() => { if (!cancelled) fetchComplaint(complaintId) }, 3_000)
          setTimeout(() => { if (!cancelled) fetchComplaint(complaintId) }, 8_000)
          setTimeout(() => { if (!cancelled) fetchComplaint(complaintId) }, 20_000)
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      wsRef.current?.close()
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

  // Poll while the pipeline is still running so we don't rely solely on the WS.
  // Stops automatically once the status leaves pending/processing.
  useEffect(() => {
    const inFlight = active?.status === 'pending' || active?.status === 'processing'
    if (!inFlight) return
    const t = setTimeout(() => fetchComplaint(id), 5_000)
    return () => clearTimeout(t)
  }, [active?.status, active?.updated_at])

  return { complaint: active, stages: activeStages, isLoading: activeLoading, error: activeError }
}
