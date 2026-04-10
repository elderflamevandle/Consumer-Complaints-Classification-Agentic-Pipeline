'use client'
import { useState } from 'react'
import { CheckCircle2, XCircle, Edit3, Loader2, AlertTriangle, ShieldAlert } from 'lucide-react'
import { useComplaintsStore } from '@/store/complaints'
import { cn } from '@/lib/utils'
import type { Complaint } from '@/types'

interface Props {
  complaint:   Complaint
  onReviewed?: () => void
}

export default function ReviewPanel({ complaint, onReviewed }: Props) {
  const { submitReview } = useComplaintsStore()
  const [action, setAction]       = useState<'approve' | 'edit' | 'reject' | null>(null)
  const [notes, setNotes]         = useState('')
  const [editedText, setEditedText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]         = useState<string | null>(null)

  if (complaint.status !== 'interrupted') return null

  const handleSubmit = async () => {
    if (!action) return
    setSubmitting(true)
    setError(null)
    try {
      await submitReview(
        complaint.id,
        action,
        notes || undefined,
        action === 'edit' ? editedText : undefined,
      )
      onReviewed?.()
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Failed to submit review')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-2xl border border-amber-500/25 bg-amber-500/[0.04] p-6 overflow-hidden relative">
      {/* Accent top bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber-500/60 via-amber-400/80 to-amber-500/60" />

      {/* ── Alert header ───────────────────────────────────── */}
      <div className="mb-5 flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-amber-500/15 border border-amber-500/25">
          <ShieldAlert className="h-4 w-4 text-amber-400" />
        </div>
        <div>
          <p className="font-semibold text-amber-300">Human Review Required</p>
          <p className="text-sm text-amber-400/70 mt-0.5 leading-relaxed">
            The AI pipeline flagged this complaint for review due to high compliance risk or
            low confidence. Please review the classification below and decide how to proceed.
          </p>
        </div>
      </div>

      {/* ── Classification summary ──────────────────────────── */}
      {complaint.classification && (
        <div className="mb-5 rounded-xl border border-white/[0.06] bg-white/[0.03] p-4">
          <p className="section-label mb-3">AI Classification</p>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            <ClassRow label="Product"    value={complaint.classification.product_type.replace(/_/g, ' ')} />
            <ClassRow label="Issue"      value={complaint.classification.issue_type.replace(/_/g, ' ')}   />
            <ClassRow label="Severity"   value={complaint.classification.severity}   severity />
            <ClassRow label="Risk"       value={complaint.classification.compliance_risk} />
            <ClassRow label="Confidence" value={`${Math.round(complaint.classification.confidence * 100)}%`} />
          </div>
        </div>
      )}

      {/* ── Action selection ────────────────────────────────── */}
      <p className="text-xs font-semibold text-foreground/80 mb-3 uppercase tracking-wider">Your Decision</p>
      <div className="mb-4 grid gap-2 sm:grid-cols-3">
        <ActionCard
          active={action === 'approve'}
          onClick={() => setAction('approve')}
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Approve"
          desc="Accept AI classification and continue pipeline"
          color="emerald"
        />
        <ActionCard
          active={action === 'edit'}
          onClick={() => setAction('edit')}
          icon={<Edit3 className="h-4 w-4" />}
          label="Edit & Continue"
          desc="Modify complaint text, then resume"
          color="indigo"
        />
        <ActionCard
          active={action === 'reject'}
          onClick={() => setAction('reject')}
          icon={<XCircle className="h-4 w-4" />}
          label="Reject"
          desc="Close complaint without processing"
          color="red"
        />
      </div>

      {/* ── Edit textarea ───────────────────────────────────── */}
      {action === 'edit' && (
        <div className="mb-4">
          <label className="mb-1.5 block text-xs font-semibold text-foreground/70 uppercase tracking-wider">
            Edited Complaint Text
          </label>
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            placeholder={complaint.scrubbed_text ?? 'Enter corrected complaint text…'}
            rows={5}
            className="field resize-y"
          />
        </div>
      )}

      {/* ── Reviewer notes ──────────────────────────────────── */}
      {action && (
        <div className="mb-4">
          <label className="mb-1.5 block text-xs font-semibold text-foreground/70 uppercase tracking-wider">
            Reviewer Notes <span className="normal-case font-normal text-muted-foreground">(optional)</span>
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add context or justification for your decision…"
            rows={3}
            className="field resize-y"
          />
        </div>
      )}

      {/* ── Error ───────────────────────────────────────────── */}
      {error && (
        <div className="mb-4 rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* ── Submit ──────────────────────────────────────────── */}
      <button
        onClick={handleSubmit}
        disabled={!action || submitting}
        className={cn(
          'btn-primary',
          action === 'approve' && 'bg-emerald-600 hover:bg-emerald-700',
          action === 'reject'  && 'bg-red-600/80 hover:bg-red-700',
        )}
      >
        {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        {submitting ? 'Submitting…' : 'Submit Decision'}
      </button>
    </div>
  )
}

/* ── Sub-components ──────────────────────────────────────────────────────── */
function ClassRow({ label, value, severity }: { label: string; value: string; severity?: boolean }) {
  const severityColor =
    value === 'CRITICAL' ? 'text-red-400' :
    value === 'HIGH'     ? 'text-orange-400' :
    value === 'MEDIUM'   ? 'text-amber-400' :
    value === 'LOW'      ? 'text-emerald-400' : 'text-foreground'

  return (
    <>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn('text-xs font-semibold col-span-1', severity ? severityColor : 'text-foreground')}>
        {value}
      </span>
    </>
  )
}

function ActionCard({
  active, onClick, icon, label, desc, color,
}: {
  active: boolean; onClick: () => void
  icon: React.ReactNode; label: string; desc: string; color: string
}) {
  const ACTIVE: Record<string, string> = {
    emerald: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
    indigo:  'border-primary/40 bg-primary/10 text-indigo-300',
    red:     'border-red-500/40 bg-red-500/10 text-red-300',
  }
  const ICON: Record<string, string> = {
    emerald: 'text-emerald-400',
    indigo:  'text-indigo-400',
    red:     'text-red-400',
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-xl border p-3.5 text-left transition-all duration-200',
        active
          ? ACTIVE[color]
          : 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.14] hover:bg-white/[0.05]'
      )}
    >
      <div className={cn('mb-1.5 flex items-center gap-2', active ? ICON[color] : 'text-muted-foreground')}>
        {icon}
        <span className={cn('text-sm font-semibold', active ? '' : 'text-foreground')}>
          {label}
        </span>
      </div>
      <p className={cn('text-xs leading-relaxed', active ? 'opacity-80' : 'text-muted-foreground')}>
        {desc}
      </p>
    </button>
  )
}
