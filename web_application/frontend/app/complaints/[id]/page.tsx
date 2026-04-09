'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, CheckCircle2, AlertCircle, Clock, ChevronDown, ChevronUp,
  FileText, Shield, BarChart3, Loader2,
} from 'lucide-react'
import Navbar from '@/components/layout/Navbar'
import PipelineView from '@/components/complaints/PipelineView'
import ReviewPanel from '@/components/complaints/ReviewPanel'
import AuditTable from '@/components/complaints/AuditTable'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/store/auth'
import { useComplaintDetail } from '@/hooks/useComplaint'
import { formatDate, statusColor, severityColor, riskColor } from '@/lib/utils'

export default function ComplaintDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { isAuthenticated, loadUser, user } = useAuthStore()
  const { complaint, stages, isLoading, error } = useComplaintDetail(id)
  const [showInternal, setShowInternal] = useState(false)

  const isAnalystOrAdmin = user?.role === 'admin' || user?.role === 'analyst'

  useEffect(() => {
    if (!isAuthenticated) loadUser().then(() => {
      if (!useAuthStore.getState().isAuthenticated) router.push('/login')
    })
  }, [])

  if (isLoading || !complaint) {
    return (
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <div className="flex items-center justify-center py-32 text-slate-400">
          {error ? (
            <div className="text-center">
              <AlertCircle className="mx-auto mb-2 h-8 w-8 text-red-400" />
              <p>{error}</p>
              <Link href="/complaints" className="mt-4 block text-sm text-blue-600 hover:underline">← Back to complaints</Link>
            </div>
          ) : (
            <div className="flex items-center gap-2"><Loader2 className="h-5 w-5 animate-spin" /> Loading…</div>
          )}
        </div>
      </div>
    )
  }

  const isProcessing = complaint.status === 'processing' || complaint.status === 'pending'
  const isComplete = complaint.status === 'complete'
  const isInterrupted = complaint.status === 'interrupted'

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">

        {/* ── Back + status header ─────────────────────────────────────── */}
        <div className="mb-6 flex items-center gap-3">
          <Link href="/complaints" className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-700 transition">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-mono text-slate-400">{id.slice(0, 12)}…</span>
        </div>

        {/* ── Status card ──────────────────────────────────────────────── */}
        <div className={`mb-6 rounded-2xl border p-5 ${
          isComplete ? 'border-emerald-200 bg-emerald-50' :
          isInterrupted ? 'border-amber-200 bg-amber-50' :
          isProcessing ? 'border-blue-200 bg-blue-50' :
          'border-red-200 bg-red-50'
        }`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              {isComplete && <CheckCircle2 className="h-6 w-6 text-emerald-600 flex-shrink-0" />}
              {isProcessing && <Loader2 className="h-6 w-6 text-blue-600 flex-shrink-0 animate-spin" />}
              {isInterrupted && <Clock className="h-6 w-6 text-amber-600 flex-shrink-0" />}
              {!isComplete && !isProcessing && !isInterrupted && (
                <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0" />
              )}
              <div>
                <p className={`font-semibold ${
                  isComplete ? 'text-emerald-800' :
                  isInterrupted ? 'text-amber-800' :
                  isProcessing ? 'text-blue-800' : 'text-red-800'
                }`}>
                  {isComplete && 'Your complaint has been reviewed'}
                  {isProcessing && 'Your complaint is being reviewed'}
                  {isInterrupted && 'Action required'}
                  {!isComplete && !isProcessing && !isInterrupted && 'Complaint needs attention'}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Submitted {formatDate(complaint.created_at)}
                  {complaint.classification?.issue_type && (
                    <> · {complaint.classification.issue_type.replace(/_/g, ' ')}</>
                  )}
                </p>
              </div>
            </div>
            <Badge variant={statusColor(complaint.status) as any} className="flex-shrink-0">
              {complaint.status}
            </Badge>
          </div>
        </div>

        {/* ── Review panel (prominent when awaiting review) ─────────────── */}
        {isInterrupted && (
          <div className="mb-6">
            <ReviewPanel complaint={complaint} />
          </div>
        )}

        {/* ── Processing indicator ──────────────────────────────────────── */}
        {isProcessing && (
          <div className="mb-6 rounded-2xl border border-blue-100 bg-white p-6 text-center">
            <Loader2 className="mx-auto mb-3 h-8 w-8 text-blue-500 animate-spin" />
            <p className="font-medium text-slate-700">AI pipeline running…</p>
            <p className="mt-1 text-sm text-slate-400">
              We're classifying your complaint, analyzing root cause, and drafting a response.
              This typically takes 15–30 seconds.
            </p>
          </div>
        )}

        {/* ── Response letter ───────────────────────────────────────────── */}
        {complaint.response_draft && (
          <div className="mb-6 rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4 flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-500" />
              <h2 className="font-semibold text-slate-800">Response</h2>
              {complaint.audit_verdict === 'PASS' && (
                <span className="ml-auto flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="h-3 w-3" /> Compliance reviewed
                </span>
              )}
            </div>
            <div className="px-6 py-5">
              <pre className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed font-sans">
                {complaint.response_draft}
              </pre>
            </div>
          </div>
        )}

        {/* ── Your complaint text ───────────────────────────────────────── */}
        {complaint.scrubbed_text && (
          <div className="mb-6 rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-800">Your Complaint</h2>
              <p className="text-xs text-slate-400 mt-0.5">Personal information has been redacted for privacy</p>
            </div>
            <div className="px-6 py-4">
              <p className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed">
                {complaint.scrubbed_text}
              </p>
            </div>
          </div>
        )}

        {/* ── Case summary ─────────────────────────────────────────────── */}
        {complaint.classification && (
          <div className="mb-6 rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
            <div className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-semibold text-slate-800">Case Summary</h2>
            </div>
            <div className="grid grid-cols-2 gap-px bg-slate-100 sm:grid-cols-3">
              <SummaryTile label="Category" value={complaint.classification.product_type.replace(/_/g, ' ')} />
              <SummaryTile label="Issue">
                <span className="text-sm font-medium text-slate-800">
                  {complaint.classification.issue_type.replace(/_/g, ' ')}
                </span>
              </SummaryTile>
              <SummaryTile label="Priority">
                <Badge variant={severityColor(complaint.classification.severity) as any}>
                  {complaint.classification.severity}
                </Badge>
              </SummaryTile>
              {complaint.assigned_team && (
                <SummaryTile label="Assigned To" value={complaint.assigned_team} className="col-span-2 sm:col-span-3" />
              )}
              {complaint.policy_citations && (
                <SummaryTile label="SLA" value={(complaint.policy_citations as any).sla_window ?? '—'} className="col-span-2 sm:col-span-3" />
              )}
            </div>
          </div>
        )}

        {/* ── Internal analysis section (analyst / admin only) ─────────── */}
        {isAnalystOrAdmin && (
          <div className="mb-6">
            <button
              onClick={() => setShowInternal((v) => !v)}
              className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-6 py-4 text-left shadow-sm hover:bg-slate-50 transition"
            >
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-slate-500" />
                <span className="font-semibold text-slate-700">Internal Analysis</span>
                <span className="text-xs text-slate-400">(analyst / admin only)</span>
              </div>
              {showInternal
                ? <ChevronUp className="h-4 w-4 text-slate-400" />
                : <ChevronDown className="h-4 w-4 text-slate-400" />
              }
            </button>

            {showInternal && (
              <div className="mt-3 space-y-4 animate-fade-in">

                {/* Pipeline */}
                <PipelineView stages={stages} status={complaint.status} />

                {/* Classification detail */}
                <InternalSection title="Classification Detail" icon={<BarChart3 className="h-4 w-4" />}>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <Tile label="Compliance Risk">
                      <Badge variant={riskColor(complaint.classification?.compliance_risk ?? '') as any}>
                        {complaint.classification?.compliance_risk}
                      </Badge>
                    </Tile>
                    <Tile label="Confidence" value={`${Math.round((complaint.classification?.confidence ?? 0) * 100)}%`} />
                    <Tile label="Audit Verdict">
                      <span className={`text-sm font-bold ${
                        complaint.audit_verdict === 'PASS' ? 'text-emerald-600' : 'text-red-600'
                      }`}>{complaint.audit_verdict ?? '—'}</span>
                    </Tile>
                  </div>
                </InternalSection>

                {/* Root cause */}
                {complaint.root_cause && (
                  <InternalSection title="Root Cause Analysis">
                    <p className="text-sm text-slate-700 leading-relaxed mb-4">{complaint.root_cause}</p>
                    {complaint.root_cause_evidence?.length > 0 && (
                      <>
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Evidence — {complaint.root_cause_evidence.length} similar cases
                        </p>
                        <div className="space-y-2">
                          {complaint.root_cause_evidence.slice(0, 3).map((ev) => (
                            <div key={ev.rank} className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-slate-700">#{ev.rank}</span>
                                <span className="text-slate-400">{ev.citation.product} / {ev.citation.issue}</span>
                                <span className="ml-auto text-slate-400">Score: {ev.score.toFixed(3)}</span>
                              </div>
                              <p>{ev.summary}</p>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </InternalSection>
                )}

                {/* Remediation */}
                {complaint.remediation_steps?.length > 0 && (
                  <InternalSection title="Remediation Plan">
                    <ol className="space-y-2">
                      {complaint.remediation_steps.map((step) => (
                        <li key={step.order} className="flex gap-3 text-sm">
                          <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                            {step.order}
                          </span>
                          <div>
                            <p className="text-slate-800">{step.action}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{step.policy_reference}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </InternalSection>
                )}

                {/* Regulatory explainer */}
                {complaint.explanation && (
                  <InternalSection title="Regulatory Audit Trail">
                    <pre className="whitespace-pre-wrap text-xs text-slate-600 leading-relaxed font-mono bg-slate-50 rounded-lg p-4 border border-slate-100 overflow-x-auto">
                      {complaint.explanation}
                    </pre>
                  </InternalSection>
                )}

                {/* Audit log */}
                <AuditTable complaintId={id} />
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  )
}

// ── Sub-components ───────────────────────────────────────────────────────────

function SummaryTile({
  label, value, children, className = '',
}: {
  label: string; value?: string; children?: React.ReactNode; className?: string
}) {
  return (
    <div className={`bg-white px-5 py-3.5 ${className}`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      {children ?? <p className="text-sm font-medium text-slate-800">{value}</p>}
    </div>
  )
}

function InternalSection({
  title, icon, children,
}: {
  title: string; icon?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 px-6 py-3.5 flex items-center gap-2">
        {icon && <span className="text-slate-400">{icon}</span>}
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      </div>
      <div className="px-6 py-4">{children}</div>
    </div>
  )
}

function Tile({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      {children ?? <p className="text-sm font-medium text-slate-900">{value}</p>}
    </div>
  )
}
