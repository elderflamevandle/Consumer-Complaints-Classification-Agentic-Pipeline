'use client'
import { CheckCircle2, Loader2, XCircle, PauseCircle, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PipelineStage } from '@/types'

/* ── Node metadata ───────────────────────────────────────────────────────── */
const NODE_META: Record<string, { label: string; desc: string; icon: string }> = {
  intake:     { label: 'Intake & PII Scrubbing',      desc: 'Sanitizing personal identifiers',       icon: '🔍' },
  classifier: { label: 'Complaint Classification',     desc: 'Product · Issue · Severity · Risk',     icon: '🧠' },
  routing:    { label: 'Routing Decision',             desc: 'Team assignment & escalation logic',    icon: '📡' },
  root_cause: { label: 'Root Cause Analysis',          desc: 'Historical pattern matching via RAG',   icon: '🔬' },
  remediator: { label: 'Remediation Planning',         desc: 'Policy-grounded action steps',          icon: '🛠' },
  writer:     { label: 'Response Drafting',            desc: 'Regulatory-compliant letter generation', icon: '✍️' },
  auditor:    { label: 'Compliance Audit',             desc: 'CFPB / FCRA / TILA verification',       icon: '⚖️' },
  explainer:  { label: 'Explanation Generation',       desc: 'Full regulatory chain-of-thought',      icon: '📋' },
}

const NODE_ORDER = ['intake','classifier','routing','root_cause','remediator','writer','auditor','explainer']

interface Props {
  stages: PipelineStage[]
  status:  string
}

/* ── Status pill styling ─────────────────────────────────────────────────── */
const STATUS_STYLES: Record<string, string> = {
  complete:    'bg-emerald-500/12 text-emerald-400 border-emerald-500/25',
  processing:  'bg-primary/12 text-indigo-400 border-primary/25',
  interrupted: 'bg-amber-500/12 text-amber-400 border-amber-500/25',
  failed:      'bg-red-500/12 text-red-400 border-red-500/25',
  pending:     'bg-white/[0.06] text-muted-foreground border-white/10',
}

export default function PipelineView({ stages, status }: Props) {
  const stageMap  = Object.fromEntries(stages.map((s) => [s.node, s]))
  const completed = stages.filter((s) => s.status === 'completed').length
  const total     = NODE_ORDER.length
  const pct       = total > 0 ? Math.round((completed / total) * 100) : 0

  /* Track fill height — proportional to completed nodes */
  const trackPct = `${(completed / total) * 100}%`

  return (
    <div className="glass-card overflow-hidden">

      {/* ── Header ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">AI Processing Pipeline</h3>
          <p className="mt-0.5 text-xs text-muted-foreground font-mono">
            {completed} / {total} nodes &nbsp;·&nbsp; {pct}% complete
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Progress arc */}
          <svg className="h-8 w-8 -rotate-90" viewBox="0 0 32 32">
            <circle cx="16" cy="16" r="12" stroke="rgba(255,255,255,0.06)" strokeWidth="3" fill="none" />
            <circle
              cx="16" cy="16" r="12"
              stroke="#6366F1"
              strokeWidth="3"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 12}`}
              strokeDashoffset={`${2 * Math.PI * 12 * (1 - pct / 100)}`}
              strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.65,0,0.35,1)', filter: 'drop-shadow(0 0 4px rgba(99,102,241,0.6))' }}
            />
          </svg>

          <span className={cn(
            'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold capitalize',
            STATUS_STYLES[status] ?? STATUS_STYLES.pending
          )}>
            {status}
          </span>
        </div>
      </div>

      {/* ── Node track ───────────────────────────────────────── */}
      <div className="relative px-5 py-5">
        {/* Vertical track */}
        <div className="pipeline-track-bg" />
        <div className="pipeline-track-fill" style={{ height: trackPct }} />

        {/* Nodes */}
        <div className="space-y-0">
          {NODE_ORDER.map((node, idx) => {
            const stage      = stageMap[node]
            const nodeStatus = stage?.status ?? 'pending'
            const meta       = NODE_META[node]
            const isLast     = idx === NODE_ORDER.length - 1

            return (
              <div key={node} className={cn('relative flex items-start gap-4', !isLast && 'pb-5')}>

                {/* ── Node indicator ── */}
                <div className="relative z-10 flex-shrink-0 mt-0.5">
                  {nodeStatus === 'completed' && (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-500/40 animate-scale-in">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    </div>
                  )}
                  {nodeStatus === 'running' && (
                    <div className="relative flex h-6 w-6 items-center justify-center">
                      <div className="node-pulse" />
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/25 border border-primary/50">
                        <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
                      </div>
                    </div>
                  )}
                  {nodeStatus === 'interrupted' && (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-500/20 border border-amber-500/40">
                      <PauseCircle className="h-3.5 w-3.5 text-amber-400" />
                    </div>
                  )}
                  {nodeStatus === 'failed' && (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20 border border-red-500/40">
                      <XCircle className="h-3.5 w-3.5 text-red-400" />
                    </div>
                  )}
                  {(nodeStatus === 'pending' || !stage) && (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-white/[0.03]">
                      <Circle className="h-3 w-3 text-white/20" />
                    </div>
                  )}
                </div>

                {/* ── Node content ── */}
                <div className="flex-1 min-w-0 pt-0.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className={cn(
                        'text-sm font-medium transition-colors',
                        nodeStatus === 'completed'  && 'text-foreground',
                        nodeStatus === 'running'    && 'text-indigo-300',
                        nodeStatus === 'interrupted'&& 'text-amber-300',
                        nodeStatus === 'failed'     && 'text-red-400',
                        (nodeStatus === 'pending' || !stage) && 'text-muted-foreground/50',
                      )}>
                        {meta?.label ?? node}
                      </p>
                      {(nodeStatus === 'pending' || !stage) && (
                        <p className="text-[11px] text-muted-foreground/30 mt-0.5">{meta?.desc}</p>
                      )}
                    </div>

                    {/* Latency badge */}
                    {(stage?.latency_ms ?? 0) > 0 && nodeStatus === 'completed' && (
                      <span className="flex-shrink-0 font-mono text-[10px] text-muted-foreground/60 bg-white/[0.04] px-1.5 py-0.5 rounded mt-0.5">
                        {stage!.latency_ms}ms
                      </span>
                    )}
                  </div>

                  {/* Running status */}
                  {nodeStatus === 'running' && (
                    <p className="mt-1 text-[11px] text-indigo-400/80 animate-pulse">
                      {(stage?.output as any)?.message ?? `Running ${meta?.desc?.toLowerCase()}…`}
                    </p>
                  )}

                  {/* Interrupted */}
                  {nodeStatus === 'interrupted' && (
                    <p className="mt-1 text-[11px] text-amber-400/80 font-medium">
                      Human review required — awaiting decision
                    </p>
                  )}

                  {/* Completed output preview */}
                  {nodeStatus === 'completed' && stage?.output && (
                    <NodeOutputPreview node={node} output={stage.output} />
                  )}

                  {/* Token count */}
                  {(stage?.tokens_used ?? 0) > 0 && nodeStatus === 'completed' && (
                    <p className="mt-1 font-mono text-[10px] text-muted-foreground/40">
                      {stage!.tokens_used} tokens
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/* ── Node output preview sub-component ──────────────────────────────────── */
function NodeOutputPreview({ node, output }: { node: string; output: Record<string, unknown> }) {
  if (node === 'classifier' && output.classification) {
    const c = output.classification as any
    return (
      <div className="mt-2 flex flex-wrap gap-1.5">
        <Chip label={c.product_type?.replace(/_/g, ' ')}  color="blue"   />
        <Chip label={c.issue_type?.replace(/_/g, ' ')}    color="purple" />
        <Chip
          label={c.severity}
          color={c.severity === 'CRITICAL' ? 'red' : c.severity === 'HIGH' ? 'orange' : 'green'}
        />
        <Chip label={`${Math.round(c.confidence * 100)}% conf`} color="slate" />
      </div>
    )
  }

  if (node === 'routing') {
    return (
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        Route: <span className="text-foreground font-medium">{output.route as string}</span>
        {Boolean(output.review_required) && (
          <span className="ml-2 text-amber-400/80 font-medium">· escalated</span>
        )}
      </p>
    )
  }

  if (node === 'root_cause' && output.root_cause) {
    return (
      <p className="mt-1.5 text-[11px] text-muted-foreground/70 line-clamp-2 leading-relaxed">
        {(output.root_cause as string).slice(0, 130)}…
      </p>
    )
  }

  if (node === 'remediator' && output.assigned_team) {
    return (
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        Assigned: <span className="text-indigo-300 font-medium">{output.assigned_team as string}</span>
      </p>
    )
  }

  if (node === 'auditor') {
    const verdict = output.verdict as string
    return (
      <p className={cn('mt-1.5 text-[11px] font-bold tracking-wide',
        verdict === 'PASS' ? 'text-emerald-400' : 'text-red-400'
      )}>
        {verdict === 'PASS' ? '✓' : '✗'} Compliance verdict: {verdict}
      </p>
    )
  }

  if (node === 'writer') {
    return (
      <p className="mt-1.5 text-[11px] text-emerald-400/80 font-medium">Response letter drafted</p>
    )
  }

  if (node === 'explainer') {
    return (
      <p className="mt-1.5 text-[11px] text-indigo-400/80 font-medium">Explanation chain generated</p>
    )
  }

  if (node === 'intake') {
    return (
      <p className="mt-1.5 text-[11px] text-emerald-400/80 font-medium">PII redacted · text normalized</p>
    )
  }

  return null
}

/* ── Chip sub-component ──────────────────────────────────────────────────── */
function Chip({ label, color }: { label: string; color: string }) {
  const COLORS: Record<string, string> = {
    blue:   'bg-blue-500/15 text-blue-300 border-blue-500/25',
    purple: 'bg-violet-500/15 text-violet-300 border-violet-500/25',
    red:    'bg-red-500/15 text-red-300 border-red-500/25',
    orange: 'bg-orange-500/15 text-orange-300 border-orange-500/25',
    green:  'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
    slate:  'bg-white/[0.06] text-muted-foreground border-white/10',
  }
  return (
    <span className={cn(
      'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold',
      COLORS[color] ?? COLORS.slate
    )}>
      {label}
    </span>
  )
}
