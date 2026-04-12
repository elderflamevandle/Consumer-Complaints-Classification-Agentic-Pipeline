'use client'
import { useState } from 'react'
import {
  Shield, Database, Zap, GitBranch, Search, Wrench,
  PenTool, CheckCircle, BookOpen, ArrowRight, ArrowDown,
  Globe, Lock, Activity, Server, Layers, Cpu, ChevronDown
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Data ─────────────────────────────────────────────────────────────────────

const PIPELINE_NODES = [
  {
    id: 'intake',
    label: 'Intake Processor',
    icon: Shield,
    color: 'indigo',
    description: 'PII scrubbing via regex + NER. Strips names, SSNs, account numbers. Returns a safe scrubbed_text.',
    inputs: ['raw_complaint', 'state_code'],
    outputs: ['intake.scrubbed_text'],
    tech: 'Rule-based PII scrubber',
    latency: '< 50ms',
  },
  {
    id: 'classifier',
    label: 'Product Classifier',
    icon: Layers,
    color: 'violet',
    description: 'Stage-1 LLM classifier. Maps complaint text to one of 11 CFPB financial product categories.',
    inputs: ['intake'],
    outputs: ['product_classification'],
    tech: 'Groq / llama-3.1-70b',
    latency: '800–1500ms',
  },
  {
    id: 'routing',
    label: 'Issue Classifier',
    icon: GitBranch,
    color: 'blue',
    description: 'Stage-2 classifier conditioned on the product. Identifies issue type, severity (LOW→CRITICAL), and compliance risk.',
    inputs: ['intake', 'product_classification'],
    outputs: ['classification (issue + severity + compliance_risk + confidence)'],
    tech: 'Groq / llama-3.1-70b',
    latency: '800–1500ms',
  },
  {
    id: 'root_cause',
    label: 'Root Cause (RAG)',
    icon: Search,
    color: 'cyan',
    description: 'Semantic search over 10,000+ CFPB complaint embeddings in ChromaDB. LLM synthesises a root-cause diagnosis from retrieved cases.',
    inputs: ['scrubbed_text'],
    outputs: ['diagnosis (root_cause + evidence_citations)'],
    tech: 'ChromaDB · bge-large-en-v1.5 · Groq',
    latency: '1000–2500ms',
  },
  {
    id: 'remediator',
    label: 'Remediator (MCP)',
    icon: Wrench,
    color: 'amber',
    description: 'Queries the local MCP policy server for state-specific SLA rules. Generates a grounded action plan with policy citations.',
    inputs: ['classification', 'diagnosis', 'state_code'],
    outputs: ['remediation (action_plan + citations)'],
    tech: 'MCP policy server · Groq',
    latency: '1000–3000ms',
  },
  {
    id: 'writer',
    label: 'Response Writer',
    icon: PenTool,
    color: 'emerald',
    description: 'Composes a 4-block CFPB-compliant customer response letter grounded in the remediation steps.',
    inputs: ['classification', 'diagnosis', 'remediation'],
    outputs: ['response_draft'],
    tech: 'Groq / llama-3.1-70b',
    latency: '1500–3500ms',
  },
  {
    id: 'auditor',
    label: 'Compliance Auditor',
    icon: CheckCircle,
    color: 'green',
    description: 'Reviews the draft for regulatory compliance, tone, and policy citation completeness. PASS → explainer; FAIL → loops back to writer (max 2 rewrites).',
    inputs: ['response_draft', 'remediation'],
    outputs: ['audit_result (verdict + failed_checks)'],
    tech: 'Groq / llama-3.1-70b · loop logic',
    latency: '800–2000ms',
  },
  {
    id: 'explainer',
    label: 'Explainer',
    icon: BookOpen,
    color: 'purple',
    description: 'Generates a deterministic 5–7 bullet audit trail summarising every pipeline decision for the compliance database.',
    inputs: ['classification', 'diagnosis', 'remediation', 'response_draft', 'audit_result'],
    outputs: ['explanation (bullets[])'],
    tech: 'Groq / llama-3.1-70b',
    latency: '800–1500ms',
  },
]

const INFRA_LAYERS = [
  {
    label: 'Frontend',
    icon: Globe,
    color: 'indigo',
    items: ['Next.js 14 + TypeScript', 'Tailwind CSS (Obsidian theme)', 'Zustand auth store', 'WebSocket live pipeline view', 'Recharts dashboards'],
  },
  {
    label: 'API Gateway',
    icon: Server,
    color: 'blue',
    items: ['FastAPI + uvicorn', 'JWT HS256/RS256 auth', 'CSRF double-submit cookie', 'slowapi rate limiting', 'bleach input sanitisation'],
  },
  {
    label: 'AI Pipeline',
    icon: Cpu,
    color: 'violet',
    items: ['LangGraph StateGraph', '8-node sequential + loop', 'asyncio.Queue → WebSocket', 'Groq API (llama-3.1-70b)', 'MCP policy server'],
  },
  {
    label: 'Data Layer',
    icon: Database,
    color: 'emerald',
    items: ['MongoDB (complaints, users, teams)', 'Redis (sessions, rate-limit)', 'ChromaDB (CFPB embeddings)', 'Motor async driver', 'bge-large-en-v1.5 embeddings'],
  },
  {
    label: 'Security',
    icon: Lock,
    color: 'amber',
    items: ['bcrypt-12 password hashing', 'Account lockout (Redis TTL)', 'IP-level brute-force guard', 'Security headers middleware', 'Team-based RBAC (4 roles)'],
  },
  {
    label: 'Observability',
    icon: Activity,
    color: 'rose',
    items: ['Append-only audit log (MongoDB)', 'Per-node latency + token tracking', 'Pipeline stage documents', 'Admin audit report UI', 'Docker Compose health checks'],
  },
]

const COLOR_MAP: Record<string, string> = {
  indigo: 'border-indigo-500/30 bg-indigo-500/8 text-indigo-400',
  violet: 'border-violet-500/30 bg-violet-500/8 text-violet-400',
  blue:   'border-blue-500/30 bg-blue-500/8 text-blue-400',
  cyan:   'border-cyan-500/30 bg-cyan-500/8 text-cyan-400',
  amber:  'border-amber-500/30 bg-amber-500/8 text-amber-400',
  emerald:'border-emerald-500/30 bg-emerald-500/8 text-emerald-400',
  green:  'border-green-500/30 bg-green-500/8 text-green-400',
  purple: 'border-purple-500/30 bg-purple-500/8 text-purple-400',
  rose:   'border-rose-500/30 bg-rose-500/8 text-rose-400',
}

const ICON_COLOR_MAP: Record<string, string> = {
  indigo: 'text-indigo-400 bg-indigo-500/12',
  violet: 'text-violet-400 bg-violet-500/12',
  blue:   'text-blue-400 bg-blue-500/12',
  cyan:   'text-cyan-400 bg-cyan-500/12',
  amber:  'text-amber-400 bg-amber-500/12',
  emerald:'text-emerald-400 bg-emerald-500/12',
  green:  'text-green-400 bg-green-500/12',
  purple: 'text-purple-400 bg-purple-500/12',
  rose:   'text-rose-400 bg-rose-500/12',
}

const DOT_COLOR: Record<string, string> = {
  indigo: 'bg-indigo-400',
  violet: 'bg-violet-400',
  blue:   'bg-blue-400',
  cyan:   'bg-cyan-400',
  amber:  'bg-amber-400',
  emerald:'bg-emerald-400',
  green:  'bg-green-400',
  purple: 'bg-purple-400',
  rose:   'bg-rose-400',
}

// ── Components ───────────────────────────────────────────────────────────────

function NodeCard({ node, index, expanded, onToggle }: {
  node: typeof PIPELINE_NODES[0]
  index: number
  expanded: boolean
  onToggle: () => void
}) {
  const Icon = node.icon
  const colorClass = COLOR_MAP[node.color]
  const iconClass  = ICON_COLOR_MAP[node.color]
  const dotClass   = DOT_COLOR[node.color]

  return (
    <div className="relative flex gap-4">
      {/* ── Timeline track ── */}
      <div className="flex flex-col items-center">
        <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border', colorClass, iconClass)}>
          <Icon className="h-4 w-4" />
        </div>
        {index < PIPELINE_NODES.length - 1 && (
          <div className="mt-1 w-px flex-1 bg-white/[0.06]" style={{ minHeight: 32 }} />
        )}
      </div>

      {/* ── Card ── */}
      <div className="mb-4 flex-1">
        <button
          onClick={onToggle}
          className="w-full text-left"
        >
          <div className={cn(
            'rounded-xl border p-4 transition-all duration-200',
            expanded
              ? cn('border-opacity-60', colorClass.split(' ')[0], 'bg-card/80')
              : 'border-white/[0.07] bg-card hover:border-white/[0.14] hover:bg-card/80'
          )}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <span className="section-label shrink-0">Node {index + 1}</span>
                <span className="text-sm font-semibold text-foreground truncate">{node.label}</span>
                <span className={cn('hidden sm:inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold', colorClass)}>
                  <div className={cn('h-1.5 w-1.5 rounded-full', dotClass)} />
                  {node.tech.split('·')[0].trim()}
                </span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="hidden sm:block text-[11px] text-muted-foreground font-mono">{node.latency}</span>
                <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform duration-200', expanded && 'rotate-180')} />
              </div>
            </div>

            {!expanded && (
              <p className="mt-2 text-xs text-muted-foreground line-clamp-1">{node.description}</p>
            )}
          </div>
        </button>

        {expanded && (
          <div className={cn('mt-1 rounded-xl border p-4 animate-fade-up', colorClass.split(' ')[0], 'border-opacity-20 bg-card/40')}>
            <p className="text-sm text-muted-foreground leading-relaxed mb-4">{node.description}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <p className="section-label mb-2">Inputs</p>
                <ul className="space-y-1">
                  {node.inputs.map(inp => (
                    <li key={inp} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <span className={cn('mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full', dotClass)} />
                      <code className="font-mono text-[11px]">{inp}</code>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="section-label mb-2">Outputs</p>
                <ul className="space-y-1">
                  {node.outputs.map(out => (
                    <li key={out} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <span className={cn('mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full', dotClass)} />
                      <code className="font-mono text-[11px]">{out}</code>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="section-label mb-2">Tech</p>
                <p className="text-xs text-muted-foreground font-mono">{node.tech}</p>
                <p className="mt-2 text-xs text-muted-foreground">Typical latency: <span className={cn('font-semibold', ICON_COLOR_MAP[node.color].split(' ')[0])}>{node.latency}</span></p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ArchitecturePage() {
  const [expandedNode, setExpandedNode] = useState<string | null>(null)
  const [tab, setTab] = useState<'pipeline' | 'infra' | 'flow'>('pipeline')

  const toggle = (id: string) => setExpandedNode(prev => prev === id ? null : id)

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">

      {/* ── Hero ── */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/8 px-4 py-1.5 text-xs font-semibold text-primary mb-5">
          <Zap className="h-3 w-3" />
          System Architecture
        </div>
        <h1 className="page-title mb-3">
          How <span className="text-gradient-indigo font-serif italic">FinComplaint AI</span> works
        </h1>
        <p className="mx-auto max-w-2xl text-sm text-muted-foreground leading-relaxed">
          An 8-node LangGraph agentic pipeline processes every consumer complaint end-to-end —
          from PII scrubbing through RAG-grounded diagnosis, MCP policy retrieval, response drafting,
          compliance audit, and explainability — all streamed live to the UI via WebSocket.
        </p>
      </div>

      {/* ── Complaint flow banner ── */}
      <div className="mb-8 glass-card p-5 overflow-x-auto">
        <p className="section-label mb-4 text-center">End-to-end complaint flow</p>
        <div className="flex items-center justify-center gap-1 min-w-max mx-auto flex-wrap">
          {['Customer submits', 'FastAPI', 'asyncio.Queue', 'LangGraph pipeline', 'MongoDB', 'WebSocket', 'UI updates live'].map((step, i, arr) => (
            <div key={step} className="flex items-center gap-1">
              <div className="rounded-lg border border-white/[0.08] bg-surface px-3 py-1.5 text-xs font-medium text-foreground whitespace-nowrap">
                {step}
              </div>
              {i < arr.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />}
            </div>
          ))}
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="mb-8 flex gap-1 rounded-xl border border-white/[0.07] bg-card p-1">
        {(['pipeline', 'infra', 'flow'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-200 capitalize',
              tab === t
                ? 'bg-primary/15 text-primary border border-primary/25'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/[0.04]'
            )}
          >
            {t === 'pipeline' ? 'AI Pipeline (8 nodes)' : t === 'infra' ? 'Infrastructure' : 'Data Flow'}
          </button>
        ))}
      </div>

      {/* ── Pipeline tab ── */}
      {tab === 'pipeline' && (
        <div className="animate-fade-up">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Click any node to expand details</p>
            <button
              onClick={() => setExpandedNode(expandedNode ? null : 'intake')}
              className="btn-ghost text-xs"
            >
              {expandedNode ? 'Collapse all' : 'Expand first'}
            </button>
          </div>

          {PIPELINE_NODES.map((node, i) => (
            <NodeCard
              key={node.id}
              node={node}
              index={i}
              expanded={expandedNode === node.id}
              onToggle={() => toggle(node.id)}
            />
          ))}

          {/* Auditor rewrite loop callout */}
          <div className="mt-2 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-500/15">
                <GitBranch className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-amber-400 mb-1">Auditor ↔ Writer Rewrite Loop</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  If the auditor finds compliance gaps, it routes back to the writer with a list of
                  <code className="mx-1 rounded bg-white/[0.06] px-1 py-0.5 font-mono text-[11px]">must_fix_items</code>.
                  Maximum 2 rewrites before the auditor force-passes to prevent infinite loops.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Infrastructure tab ── */}
      {tab === 'infra' && (
        <div className="animate-fade-up grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {INFRA_LAYERS.map(layer => {
            const Icon = layer.icon
            const colorClass = COLOR_MAP[layer.color]
            const iconClass  = ICON_COLOR_MAP[layer.color]
            const dotClass   = DOT_COLOR[layer.color]
            return (
              <div key={layer.label} className="glass-card p-4">
                <div className="flex items-center gap-2.5 mb-4">
                  <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg border', colorClass, iconClass)}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <p className="text-sm font-semibold text-foreground">{layer.label}</p>
                </div>
                <ul className="space-y-2">
                  {layer.items.map(item => (
                    <li key={item} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className={cn('mt-1 h-1.5 w-1.5 shrink-0 rounded-full', dotClass)} />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}

          {/* Docker compose diagram */}
          <div className="sm:col-span-2 lg:col-span-3 glass-card p-5">
            <p className="section-label mb-4">Docker Compose — one command to run everything</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { name: 'redis', desc: 'redis:7-alpine', color: 'rose', note: 'Rate limiting · sessions' },
                { name: 'mongodb', desc: 'mongo:7', color: 'emerald', note: 'Documents · audit logs' },
                { name: 'backend', desc: 'python:3.11-slim', color: 'indigo', note: 'FastAPI · LangGraph · :8000' },
                { name: 'frontend', desc: 'node:20-alpine', color: 'violet', note: 'Next.js standalone · :3000' },
              ].map(svc => (
                <div key={svc.name} className={cn('rounded-xl border p-3', COLOR_MAP[svc.color])}>
                  <p className="text-xs font-bold mb-1">{svc.name}</p>
                  <p className="font-mono text-[10px] opacity-70 mb-1">{svc.desc}</p>
                  <p className="text-[10px] opacity-60">{svc.note}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Data flow tab ── */}
      {tab === 'flow' && (
        <div className="animate-fade-up space-y-4">
          {[
            {
              step: '1', title: 'User submits complaint',
              color: 'indigo',
              detail: 'POST /api/complaints with complaint_text + state_code. CSRF-protected, rate-limited, sanitised. Complaint document created in MongoDB with status=pending.',
              fields: ['complaint_text (raw)', 'state_code', 'user_id (from JWT)'],
            },
            {
              step: '2', title: 'Pipeline fires immediately',
              color: 'violet',
              detail: 'asyncio.create_task() launches the pipeline worker in the background. An asyncio.Queue is created and registered in the in-memory pipeline registry. Status set to processing.',
              fields: ['asyncio.Queue created', 'complaint status → processing', '8 stage docs initialised as pending'],
            },
            {
              step: '3', title: 'LangGraph streams node-by-node',
              color: 'blue',
              detail: 'graph.astream(initial_state) yields {node_name: state_updates} for each completed node. PipelineRunner maps each update to a typed WebSocket payload and pushes it to the Queue.',
              fields: ['intake → scrubbed_text', 'product_classifier → ProductClassificationResult', 'issue_classifier → ClassificationResult', 'root_cause → RootCauseResult (RAG)', 'remediator → RemediationResult (MCP)', 'response_writer → ResponseDraft', 'response_auditor → ResponseAuditResult', 'explainer → ExplanationResult'],
            },
            {
              step: '4', title: 'WebSocket pushes to frontend',
              color: 'cyan',
              detail: 'The WebSocket handler at /api/complaints/ws/{id} drains the Queue and forwards each pipeline_update message to the connected browser. The PipelineView component renders nodes live.',
              fields: ['type: pipeline_update (per node)', 'type: pipeline_done (end signal)', 'type: final_state (complete complaint + all stages)'],
            },
            {
              step: '5', title: 'Results persisted to MongoDB',
              color: 'emerald',
              detail: 'After all nodes complete, the final PipelineState is serialised and written to the complaint document. Each stage\'s output, latency, and token count is stored in pipeline_stages collection.',
              fields: ['classification (product + issue + severity)', 'root_cause + evidence_citations', 'remediation_steps + policy_citations', 'response_draft (customer letter)', 'audit_verdict (PASS/FAIL)', 'explanation bullets[]', 'status → complete'],
            },
          ].map(({ step, title, color, detail, fields }) => {
            const dotClass = DOT_COLOR[color]
            const colorClass = COLOR_MAP[color]
            return (
              <div key={step} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-bold', colorClass)}>
                    {step}
                  </div>
                  {step !== '5' && <div className="mt-1 w-px flex-1 bg-white/[0.06]" style={{ minHeight: 24 }} />}
                </div>
                <div className="mb-4 flex-1 glass-card p-4">
                  <p className="text-sm font-semibold text-foreground mb-2">{title}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed mb-3">{detail}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {fields.map(f => (
                      <span key={f} className="rounded-md border border-white/[0.07] bg-surface px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Stats strip ── */}
      <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Pipeline nodes',    value: '8',    sub: 'LangGraph graph',    color: 'indigo' },
          { label: 'Avg completion',    value: '~15s', sub: 'end-to-end',         color: 'emerald' },
          { label: 'CFPB complaints',   value: '10K+', sub: 'ChromaDB index',     color: 'violet' },
          { label: 'Max rewrite loops', value: '2',    sub: 'auditor → writer',   color: 'amber' },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className={cn('glass-card p-4 border-t-2', `border-t-${color}-500/40`)}>
            <p className={cn('font-serif text-3xl font-normal mb-0.5', ICON_COLOR_MAP[color].split(' ')[0])}>{value}</p>
            <p className="text-xs font-semibold text-foreground">{label}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{sub}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
