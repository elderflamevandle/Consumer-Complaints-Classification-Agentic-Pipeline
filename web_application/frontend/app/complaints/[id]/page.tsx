'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, CheckCircle2, AlertCircle, Clock,
  FileText, Shield, Loader2, Cpu, Pencil, X, Check, Lock,
} from 'lucide-react'
import type { ResponseDraftData } from '@/types'
import { cn } from '@/lib/utils'
import Navbar from '@/components/layout/Navbar'
import PipelineView from '@/components/complaints/PipelineView'
import ReviewPanel from '@/components/complaints/ReviewPanel'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/auth'
import { useComplaintsStore } from '@/store/complaints'
import { useComplaintDetail } from '@/hooks/useComplaint'
import { complaintsApi } from '@/lib/api-client'
import { formatDate, statusColor, severityColor } from '@/lib/utils'

export default function ComplaintDetailPage() {
  const { id }   = useParams<{ id: string }>()
  const router   = useRouter()
  const { isAuthenticated, loadUser, user } = useAuthStore()
  const { complaint, stages, isLoading, error } = useComplaintDetail(id)
  const fetchComplaint = useComplaintsStore((s) => s.fetchComplaint)
  const [editingResponse, setEditingResponse] = useState(false)
  const [responseDraft, setResponseDraft]     = useState('')
  const [savingResponse, setSavingResponse]   = useState(false)

  const isAnalystOrAdmin = user?.role === 'admin' || user?.role === 'analyst'

  useEffect(() => {
    if (!isAuthenticated)
      loadUser().then(() => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
  }, [])

  /* ── Loading / error ── */
  if (isLoading || !complaint) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center py-32">
          {error ? (
            <div className="text-center animate-fade-up">
              <div className="mb-4 mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10 border border-red-500/20">
                <AlertCircle className="h-6 w-6 text-red-400" />
              </div>
              <p className="text-sm text-foreground/70">{error}</p>
              <Link href="/complaints" className="mt-4 inline-block text-sm text-primary hover:text-indigo-300 transition-colors">
                ← Back to complaints
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-muted-foreground animate-fade-in">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">Loading complaint…</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  const isComplete    = complaint.status === 'complete'
  const isProcessing  = complaint.status === 'processing' || complaint.status === 'pending'
  const isInterrupted = complaint.status === 'interrupted'
  const isFailed      = !isComplete && !isProcessing && !isInterrupted

  /* ── Response letter helpers ── */
  const rd         = complaint.response_draft
  const structured: ResponseDraftData | null =
    rd && typeof rd === 'object' && 'external' in rd ? rd as ResponseDraftData : null
  const ext            = structured?.external
  const externalAsText = ext
    ? `${ext.acknowledgment}\n\n${ext.findings}\n\n${ext.timeline}`
    : (typeof rd === 'string' ? rd : '')

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

        {/* ── Breadcrumb ─────────────────────────────────────────── */}
        <div className="mb-6 flex items-center gap-2 text-sm animate-fade-up">
          <Link href="/complaints" className="btn-ghost gap-1.5 px-2 py-1 text-sm">
            <ArrowLeft className="h-3.5 w-3.5" /> Complaints
          </Link>
          <span className="text-white/10">/</span>
          <span className="font-mono text-xs text-muted-foreground">{id.slice(0, 16)}…</span>
        </div>

        {/* ── Two-column grid ─────────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:items-start">

          {/* ══════════════ LEFT COLUMN ══════════════ */}
          <div className="space-y-5">

            {/* Response Letter */}
            {rd && (
              <div className="glass-card overflow-hidden animate-fade-up delay-75">
                {/* Header */}
                <div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-4">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                    <FileText className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <h2 className="text-sm font-semibold text-foreground">Response Letter</h2>
                  {complaint.audit_verdict === 'PASS' && !editingResponse && (
                    <span className="ml-1 flex items-center gap-1 rounded-full bg-emerald-500/12 border border-emerald-500/25 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                      <CheckCircle2 className="h-2.5 w-2.5" /> Compliance reviewed
                    </span>
                  )}
                  {isAnalystOrAdmin && !editingResponse && (
                    <button
                      onClick={() => { setResponseDraft(externalAsText); setEditingResponse(true) }}
                      className="ml-auto flex items-center gap-1 rounded-lg border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground hover:border-white/[0.15] transition-all"
                    >
                      <Pencil className="h-3 w-3" /> Edit
                    </button>
                  )}
                  {editingResponse && (
                    <div className="ml-auto flex items-center gap-2">
                      <button
                        onClick={async () => {
                          setSavingResponse(true)
                          try {
                            await complaintsApi.updateResponse(id, responseDraft)
                            setEditingResponse(false)
                            await fetchComplaint(id)
                          } finally {
                            setSavingResponse(false)
                          }
                        }}
                        disabled={savingResponse}
                        className="flex items-center gap-1 rounded-lg bg-primary/20 border border-primary/30 px-2.5 py-1 text-xs text-primary hover:bg-primary/30 transition-all disabled:opacity-50"
                      >
                        {savingResponse ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                        Save
                      </button>
                      <button
                        onClick={() => setEditingResponse(false)}
                        className="flex items-center gap-1 rounded-lg border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground transition-all"
                      >
                        <X className="h-3 w-3" /> Cancel
                      </button>
                    </div>
                  )}
                </div>

                {/* Body */}
                <div className="px-5 py-5 space-y-5">
                  {editingResponse ? (
                    <textarea
                      value={responseDraft}
                      onChange={(e) => setResponseDraft(e.target.value)}
                      rows={16}
                      className="field w-full resize-y font-mono text-xs leading-relaxed"
                    />
                  ) : structured ? (
                    <ResponseSection
                      label="Customer Response"
                      showHeadings={false}
                      fields={[
                        { heading: 'Acknowledgment', text: structured.external.acknowledgment },
                        { heading: 'Findings',        text: structured.external.findings },
                        { heading: 'Timeline',        text: structured.external.timeline },
                      ]}
                    />
                  ) : (
                    <ResponseSection
                      label="Customer Response"
                      showHeadings={false}
                      fields={parseResponseText(typeof rd === 'string' ? rd : JSON.stringify(rd, null, 2))
                        .map((text, i) => ({ heading: String(i), text }))}
                    />
                  )}
                </div>
              </div>
            )}

            {/* SLA Guidelines & Policies — separate card, admin / analyst only */}
            {isAnalystOrAdmin && rd && !editingResponse && (() => {
              if (structured) {
                const hasContent =
                  structured.internal.resolution_summary ||
                  structured.internal.action_steps.length > 0 ||
                  structured.policy_citation_labels.length > 0
                if (!hasContent) return null
                return (
                  <InternalAmberBlock>
                    {structured.internal.resolution_summary && (
                      <div>
                        <p className="section-label mb-1.5">Resolution Summary</p>
                        <p className="text-sm text-foreground/80 leading-relaxed">
                          {structured.internal.resolution_summary}
                        </p>
                      </div>
                    )}
                    {structured.internal.action_steps.length > 0 && (
                      <ActionStepsList steps={structured.internal.action_steps.map(s => ({ action: s }))} />
                    )}
                    {structured.policy_citation_labels.length > 0 && (
                      <div>
                        <p className="section-label mb-1.5">Policy Citations</p>
                        <div className="flex flex-wrap gap-1.5">
                          {structured.policy_citation_labels.map((label, i) => (
                            <span key={i} className="rounded-full bg-white/[0.06] border border-white/[0.08] px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                              {label}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </InternalAmberBlock>
                )
              }
              // Fallback: reconstruct from top-level complaint fields
              if (!complaint.root_cause && !(complaint.remediation_steps?.length > 0) && !complaint.policy_citations) return null
              return (
                <InternalAmberBlock>
                  {complaint.root_cause && (
                    <div>
                      <p className="section-label mb-1.5">Resolution Summary</p>
                      <p className="text-sm text-foreground/80 leading-relaxed">{complaint.root_cause}</p>
                    </div>
                  )}
                  {complaint.remediation_steps?.length > 0 && (
                    <ActionStepsList steps={complaint.remediation_steps} />
                  )}
                  {complaint.policy_citations && (
                    <div>
                      <p className="section-label mb-1.5">Policy Citations</p>
                      <div className="space-y-1.5">
                        {(complaint.policy_citations as any).sla_window && (
                          <PolicyRow label="SLA Window" value={(complaint.policy_citations as any).sla_window} />
                        )}
                        {(complaint.policy_citations as any).regulatory_basis && (
                          <PolicyRow label="Regulatory" value={(complaint.policy_citations as any).regulatory_basis} />
                        )}
                        {(complaint.policy_citations as any).required_actions && (
                          <PolicyRow label="Required" value={(complaint.policy_citations as any).required_actions} />
                        )}
                      </div>
                    </div>
                  )}
                </InternalAmberBlock>
              )
            })()}

            {/* Processing indicator */}
            {isProcessing && (
              <div className="glass-card p-8 text-center animate-fade-up delay-150">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 border border-primary/20">
                  <Cpu className="h-6 w-6 text-primary animate-pulse" />
                </div>
                <p className="font-serif text-lg text-foreground">Processing your complaint</p>
                <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
                  The 8-node AI pipeline is running — classifying, analyzing root cause, and drafting a response.
                  Typically takes 15–30 seconds.
                </p>
                <div className="mt-5 flex items-center justify-center gap-1.5">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce"
                      style={{ animationDelay: `${i * 150}ms` }} />
                  ))}
                </div>
              </div>
            )}

          </div>

          {/* ══════════════ RIGHT COLUMN (sidebar) ══════════════ */}
          <div className="space-y-5">

            {/* Status card */}
            <div className={cn(
              'rounded-2xl border p-5 relative overflow-hidden animate-fade-up delay-75',
              isComplete    && 'border-emerald-500/25 bg-emerald-500/[0.05]',
              isInterrupted && 'border-amber-500/25 bg-amber-500/[0.05]',
              isProcessing  && 'border-primary/25 bg-primary/[0.05]',
              isFailed      && 'border-red-500/25 bg-red-500/[0.05]',
            )}>
              <div className={cn(
                'absolute top-0 left-0 right-0 h-0.5',
                isComplete    && 'bg-gradient-to-r from-transparent via-emerald-500/70 to-transparent',
                isInterrupted && 'bg-gradient-to-r from-transparent via-amber-500/70 to-transparent',
                isProcessing  && 'bg-gradient-to-r from-transparent via-primary/70 to-transparent',
                isFailed      && 'bg-gradient-to-r from-transparent via-red-500/70 to-transparent',
              )} />
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border',
                    isComplete    && 'bg-emerald-500/15 border-emerald-500/30',
                    isInterrupted && 'bg-amber-500/15 border-amber-500/30',
                    isProcessing  && 'bg-primary/15 border-primary/30',
                    isFailed      && 'bg-red-500/15 border-red-500/30',
                  )}>
                    {isComplete    && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                    {isProcessing  && <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />}
                    {isInterrupted && <Clock className="h-4 w-4 text-amber-400" />}
                    {isFailed      && <AlertCircle className="h-4 w-4 text-red-400" />}
                  </div>
                  <div>
                    <p className={cn(
                      'text-sm font-semibold',
                      isComplete    && 'text-emerald-300',
                      isInterrupted && 'text-amber-300',
                      isProcessing  && 'text-indigo-300',
                      isFailed      && 'text-red-300',
                    )}>
                      {isComplete    && 'Complaint fully processed'}
                      {isProcessing  && 'AI pipeline running…'}
                      {isInterrupted && 'Action required from reviewer'}
                      {isFailed      && 'Complaint needs attention'}
                    </p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                      Submitted {formatDate(complaint.created_at)}
                      {complaint.classification?.issue_type && (
                        <> &nbsp;·&nbsp; {complaint.classification.issue_type.replace(/_/g, ' ')}</>
                      )}
                    </p>
                  </div>
                </div>
                <Badge variant={statusColor(complaint.status) as any} className="flex-shrink-0">
                  {complaint.status}
                </Badge>
              </div>
            </div>

            {/* Review panel */}
            {isInterrupted && (
              <div className="animate-fade-up delay-100">
                <ReviewPanel complaint={complaint} />
              </div>
            )}

            {/* Case Summary */}
            {complaint.classification && (
              <div className="glass-card overflow-hidden animate-fade-up delay-150">
                <div className="border-b border-white/[0.06] px-5 py-4">
                  <h2 className="text-sm font-semibold text-foreground">Case Summary</h2>
                </div>
                <div className="divide-y divide-white/[0.04]">
                  <SummaryRow label="Product Type"
                    value={complaint.classification.product_type.replace(/_/g, ' ')} />
                  <SummaryRow label="Issue Type"
                    value={complaint.classification.issue_type.replace(/_/g, ' ')} />
                  <SummaryRow label="Priority">
                    <Badge variant={severityColor(complaint.classification.severity) as any}>
                      {complaint.classification.severity}
                    </Badge>
                  </SummaryRow>
                  {complaint.assigned_team && (
                    <SummaryRow label="Assigned Team" value={complaint.assigned_team} />
                  )}
                  {complaint.policy_citations && (complaint.policy_citations as any).sla_window && (
                    <SummaryRow label="SLA Window"
                      value={(complaint.policy_citations as any).sla_window} />
                  )}
                </div>
              </div>
            )}

            {/* Complaint Details */}
            {complaint.scrubbed_text && (
              <div className="glass-card overflow-hidden animate-fade-up delay-175">
                <div className="flex items-center gap-2 border-b border-white/[0.06] px-5 py-4">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">Complaint Details</h2>
                    <p className="font-mono text-[10px] text-muted-foreground mt-0.5">ID: {id}</p>
                  </div>
                  <span className="ml-auto text-[10px] text-muted-foreground">PII automatically redacted</span>
                </div>
                <div className="px-5 py-4">
                  <p className="whitespace-pre-wrap text-sm text-foreground/75 leading-relaxed">
                    {complaint.scrubbed_text}
                  </p>
                </div>
              </div>
            )}

            {/* Internal Analysis — always expanded in sidebar for admin/analyst */}
            {isAnalystOrAdmin && (
              <div className="animate-fade-up delay-200">
                <PipelineView stages={stages} status={complaint.status} />
              </div>
            )}

          </div>
          {/* ══════════════ END GRID ══════════════ */}
        </div>
      </main>
    </div>
  )
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function parseResponseText(text: string): string[] {
  const parts = text
    .split(/(?:Acknowledgm?ent|Findings|Timeline)\s*:\s*/i)
    .map(s => s.trim())
    .filter(Boolean)
  return parts.length > 1 ? parts : [text]
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function SummaryRow({
  label, value, children,
}: {
  label: string; value?: string; children?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-3 px-5 py-3">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60 flex-shrink-0 mt-0.5 w-28">
        {label}
      </span>
      {children ?? (
        <span className="text-sm font-medium text-foreground/90 text-right">{value}</span>
      )}
    </div>
  )
}

function InternalAmberBlock({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] animate-fade-up">
      <div className="flex items-center gap-2 border-b border-amber-500/15 px-5 py-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/15 border border-amber-500/25">
          <Lock className="h-3.5 w-3.5 text-amber-400" />
        </div>
        <h2 className="text-sm font-semibold text-amber-300">SLA Guidelines &amp; Policies</h2>
      </div>
      <div className="px-5 py-5 space-y-4">{children}</div>
    </div>
  )
}

function ActionStepsList({ steps }: { steps: any[] }) {
  return (
    <div>
      <p className="section-label mb-2">Action Steps</p>
      <ol className="space-y-2">
        {steps.map((step: any, i: number) => {
          const isObj  = step && typeof step === 'object'
          const action = isObj ? (step.action ?? String(step)) : String(step)
          return (
            <li key={i} className="flex gap-2.5 text-sm">
              <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-amber-500/20 border border-amber-500/30 font-mono text-[9px] font-bold text-amber-400 mt-0.5">
                {i + 1}
              </span>
              <span className="text-foreground/75 leading-relaxed">{action}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function PolicyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 w-24 flex-shrink-0 mt-0.5">
        {label}
      </span>
      <span className="text-sm text-foreground/80">{value}</span>
    </div>
  )
}

function ResponseSection({
  label,
  fields,
  showHeadings = true,
}: {
  label: string
  fields: { heading: string; text: string }[]
  showHeadings?: boolean
}) {
  return (
    <div>
      <p className="section-label mb-3">{label}</p>
      <div className="space-y-4">
        {fields.map(({ heading, text }) => (
          <div key={heading}>
            {showHeadings && (
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                {heading}
              </p>
            )}
            <p className="text-sm text-foreground/85 leading-relaxed">{text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
