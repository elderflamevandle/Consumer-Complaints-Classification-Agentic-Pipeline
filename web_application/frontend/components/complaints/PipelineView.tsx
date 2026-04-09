'use client'
import { CheckCircle2, Circle, Loader2, XCircle, PauseCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PipelineStage } from '@/types'

const NODE_LABELS: Record<string, string> = {
  intake: 'Intake & PII Scrubbing',
  classifier: 'Complaint Classification',
  routing: 'Routing Decision',
  root_cause: 'Root Cause Analysis',
  remediator: 'Remediation Planning',
  writer: 'Response Drafting',
  auditor: 'Compliance Audit',
  explainer: 'Explanation Generation',
}

const NODE_ORDER = ['intake','classifier','routing','root_cause','remediator','writer','auditor','explainer']

interface Props {
  stages: PipelineStage[]
  status: string
}

export default function PipelineView({ stages, status }: Props) {
  const stageMap = Object.fromEntries(stages.map((s) => [s.node, s]))
  const completed = stages.filter((s) => s.status === 'completed').length
  const total = NODE_ORDER.length
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 px-6 py-4 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">AI Pipeline</h3>
          <p className="text-xs text-slate-500 mt-0.5">{completed} of {total} nodes complete</p>
        </div>
        <div className="text-right">
          <span className={cn(
            'inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold',
            status === 'complete' && 'bg-emerald-100 text-emerald-800',
            status === 'processing' && 'bg-blue-100 text-blue-800',
            status === 'interrupted' && 'bg-amber-100 text-amber-800',
            status === 'failed' && 'bg-red-100 text-red-800',
            status === 'pending' && 'bg-slate-100 text-slate-600',
          )}>
            {status}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-100">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Node list */}
      <div className="divide-y divide-slate-50">
        {NODE_ORDER.map((node, idx) => {
          const stage = stageMap[node]
          const nodeStatus = stage?.status ?? 'pending'

          return (
            <div key={node} className="flex items-start gap-4 px-6 py-3.5">
              {/* Icon */}
              <div className="mt-0.5 flex-shrink-0">
                {nodeStatus === 'completed' && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
                {nodeStatus === 'running' && <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />}
                {nodeStatus === 'failed' && <XCircle className="h-5 w-5 text-red-500" />}
                {nodeStatus === 'interrupted' && <PauseCircle className="h-5 w-5 text-amber-500" />}
                {(nodeStatus === 'pending' || !stage) && (
                  <Circle className="h-5 w-5 text-slate-300" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className={cn(
                    'text-sm font-medium',
                    nodeStatus === 'completed' ? 'text-slate-900' :
                    nodeStatus === 'running' ? 'text-blue-700' :
                    nodeStatus === 'failed' ? 'text-red-700' :
                    'text-slate-400',
                  )}>
                    {NODE_LABELS[node] ?? node}
                  </p>
                  {(stage?.latency_ms ?? 0) > 0 && (
                    <span className="text-xs text-slate-400 flex-shrink-0">{stage!.latency_ms}ms</span>
                  )}
                </div>

                {/* Output preview */}
                {nodeStatus === 'completed' && stage?.output && (
                  <NodeOutputPreview node={node} output={stage.output} />
                )}
                {nodeStatus === 'running' && (
                  <p className="text-xs text-blue-500 mt-0.5 animate-pulse">
                    {(stage?.output as any)?.message ?? 'Processing…'}
                  </p>
                )}
                {nodeStatus === 'interrupted' && (
                  <p className="text-xs text-amber-600 mt-0.5 font-medium">
                    Human review required — awaiting decision
                  </p>
                )}
                {(stage?.tokens_used ?? 0) > 0 && nodeStatus === 'completed' && (
                  <p className="text-xs text-slate-400 mt-0.5">{stage.tokens_used} tokens</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function NodeOutputPreview({ node, output }: { node: string; output: Record<string, unknown> }) {
  if (node === 'classifier' && output.classification) {
    const c = output.classification as any
    return (
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        <Chip label={c.product_type?.replace(/_/g, ' ')} color="blue" />
        <Chip label={c.issue_type?.replace(/_/g, ' ')} color="purple" />
        <Chip label={c.severity} color={c.severity === 'CRITICAL' || c.severity === 'HIGH' ? 'red' : 'green'} />
        <Chip label={`${Math.round(c.confidence * 100)}% confidence`} color="slate" />
      </div>
    )
  }
  if (node === 'routing') {
    return (
      <p className="mt-1 text-xs text-slate-500">
        Route: <span className="font-medium">{output.route as string}</span>
        {Boolean(output.review_required) && ' — review required'}
      </p>
    )
  }
  if (node === 'root_cause' && output.root_cause) {
    return (
      <p className="mt-1 text-xs text-slate-500 line-clamp-2">
        {(output.root_cause as string).slice(0, 120)}…
      </p>
    )
  }
  if (node === 'remediator' && output.assigned_team) {
    return (
      <p className="mt-1 text-xs text-slate-500">
        Team: <span className="font-medium">{output.assigned_team as string}</span>
      </p>
    )
  }
  if (node === 'auditor') {
    const verdict = output.verdict as string
    return (
      <p className={`mt-1 text-xs font-semibold ${verdict === 'PASS' ? 'text-emerald-600' : 'text-red-600'}`}>
        Verdict: {verdict}
      </p>
    )
  }
  return null
}

function Chip({ label, color }: { label: string; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700',
    purple: 'bg-violet-50 text-violet-700',
    red: 'bg-red-50 text-red-700',
    green: 'bg-emerald-50 text-emerald-700',
    slate: 'bg-slate-100 text-slate-600',
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[color] ?? colors.slate}`}>
      {label}
    </span>
  )
}
