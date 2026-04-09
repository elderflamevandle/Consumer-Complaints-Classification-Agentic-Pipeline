'use client'
import { useState } from 'react'
import { CheckCircle2, XCircle, Edit3, Loader2, AlertTriangle } from 'lucide-react'
import { useComplaintsStore } from '@/store/complaints'
import type { Complaint } from '@/types'

interface Props {
  complaint: Complaint
  onReviewed?: () => void
}

export default function ReviewPanel({ complaint, onReviewed }: Props) {
  const { submitReview } = useComplaintsStore()
  const [action, setAction] = useState<'approve' | 'edit' | 'reject' | null>(null)
  const [notes, setNotes] = useState('')
  const [editedText, setEditedText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    <div className="rounded-2xl border-2 border-amber-200 bg-amber-50 p-6 shadow-sm">
      {/* Alert banner */}
      <div className="mb-5 flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
        <div>
          <p className="font-semibold text-amber-900">Human Review Required</p>
          <p className="text-sm text-amber-700 mt-0.5">
            The AI pipeline flagged this complaint for review due to high compliance risk or low confidence.
            Please review the classification and decide how to proceed.
          </p>
        </div>
      </div>

      {/* Classification summary */}
      {complaint.classification && (
        <div className="mb-5 rounded-xl bg-white border border-amber-100 p-4 text-sm">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">AI Classification</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-slate-700">
            <Row label="Product" value={complaint.classification.product_type.replace(/_/g, ' ')} />
            <Row label="Issue" value={complaint.classification.issue_type.replace(/_/g, ' ')} />
            <Row label="Severity" value={complaint.classification.severity} />
            <Row label="Compliance Risk" value={complaint.classification.compliance_risk} />
            <Row label="Confidence" value={`${Math.round(complaint.classification.confidence * 100)}%`} />
          </div>
        </div>
      )}

      {/* Action selection */}
      <p className="mb-3 text-sm font-semibold text-slate-800">Your Decision</p>
      <div className="mb-4 grid gap-2.5 sm:grid-cols-3">
        <ActionCard
          active={action === 'approve'}
          onClick={() => setAction('approve')}
          icon={<CheckCircle2 className="h-5 w-5 text-emerald-600" />}
          label="Approve"
          desc="Accept AI classification and continue pipeline"
          color="emerald"
        />
        <ActionCard
          active={action === 'edit'}
          onClick={() => setAction('edit')}
          icon={<Edit3 className="h-5 w-5 text-blue-600" />}
          label="Edit & Continue"
          desc="Modify complaint text, then resume"
          color="blue"
        />
        <ActionCard
          active={action === 'reject'}
          onClick={() => setAction('reject')}
          icon={<XCircle className="h-5 w-5 text-red-600" />}
          label="Reject"
          desc="Close this complaint without processing"
          color="red"
        />
      </div>

      {/* Edit text area */}
      {action === 'edit' && (
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-slate-700">
            Edited Complaint Text
          </label>
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            placeholder={complaint.scrubbed_text ?? 'Enter corrected complaint text…'}
            rows={5}
            className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition resize-y"
          />
        </div>
      )}

      {/* Reviewer notes */}
      {action && (
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-medium text-slate-700">
            Reviewer Notes (optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add context or justification for your decision…"
            rows={3}
            className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition resize-y"
          />
        </div>
      )}

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">{error}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={!action || submitting}
        className="flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50 transition"
      >
        {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        {submitting ? 'Submitting…' : 'Submit Decision'}
      </button>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="text-slate-500">{label}</span>
      <span className="font-medium">{value}</span>
    </>
  )
}

function ActionCard({
  active, onClick, icon, label, desc, color,
}: {
  active: boolean; onClick: () => void
  icon: React.ReactNode; label: string; desc: string; color: string
}) {
  const colors: Record<string, string> = {
    emerald: 'border-emerald-400 bg-emerald-50',
    blue: 'border-blue-400 bg-blue-50',
    red: 'border-red-400 bg-red-50',
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border-2 p-3.5 text-left transition ${
        active ? colors[color] : 'border-slate-200 bg-white hover:border-slate-300'
      }`}
    >
      <div className="mb-1.5 flex items-center gap-2">
        {icon}
        <span className="text-sm font-semibold text-slate-900">{label}</span>
      </div>
      <p className="text-xs text-slate-500">{desc}</p>
    </button>
  )
}
