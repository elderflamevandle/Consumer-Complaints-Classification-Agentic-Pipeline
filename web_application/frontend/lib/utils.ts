import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function severityColor(s: string | null | undefined): string {
  switch (s) {
    case 'CRITICAL': return 'destructive'
    case 'HIGH':     return 'warning'
    case 'MEDIUM':   return 'info'
    case 'LOW':      return 'success'
    default:         return 'secondary'
  }
}

export function statusColor(s: string | null | undefined): string {
  switch (s) {
    case 'complete':    return 'success'
    case 'processing':  return 'info'
    case 'interrupted': return 'warning'
    case 'failed':      return 'destructive'
    case 'rejected':    return 'destructive'
    default:            return 'secondary'
  }
}

export function riskColor(r: string | null | undefined): string {
  switch (r) {
    case 'HIGH':   return 'destructive'
    case 'MEDIUM': return 'warning'
    case 'LOW':    return 'success'
    default:       return 'secondary'
  }
}
