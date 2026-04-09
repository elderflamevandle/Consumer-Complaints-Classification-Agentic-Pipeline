import Link from 'next/link'
import { Shield, Zap, Search, FileText, CheckCircle, BarChart3 } from 'lucide-react'

export const metadata = {
  title: 'FinComplaint AI — Financial Complaint Triage',
  description: 'AI-powered complaint triage, classification, and remediation for financial services.',
}

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
      {/* Nav */}
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2 font-bold text-white">
          <Shield className="h-5 w-5 text-blue-400" />
          FinComplaint AI
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm font-medium text-slate-300 hover:text-white transition">
            Sign in
          </Link>
          <Link href="/register" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 transition">
            Get started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-xs font-semibold text-blue-300">
          <Zap className="h-3 w-3" /> Powered by Groq + ChromaDB + MongoDB Atlas
        </div>
        <h1 className="mb-6 text-5xl font-extrabold tracking-tight text-white sm:text-6xl">
          AI-Powered Financial<br />
          <span className="text-blue-400">Complaint Triage</span>
        </h1>
        <p className="mx-auto mb-10 max-w-2xl text-lg text-slate-400 leading-relaxed">
          Automatically classify complaints by product, issue type, severity, and compliance risk.
          Identify root causes, generate policy-grounded remediation plans, and produce
          regulatory-compliant response letters — all with full explainability for regulators.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link href="/register" className="rounded-xl bg-blue-600 px-8 py-3.5 text-sm font-semibold text-white hover:bg-blue-500 transition shadow-lg shadow-blue-500/20">
            Start for free →
          </Link>
          <Link href="/login" className="rounded-xl border border-slate-700 bg-slate-800/50 px-8 py-3.5 text-sm font-semibold text-slate-300 hover:bg-slate-700 transition">
            Sign in
          </Link>
        </div>
      </section>

      {/* Pipeline steps */}
      <section className="mx-auto max-w-7xl px-6 py-16">
        <p className="mb-8 text-center text-sm font-semibold uppercase tracking-wider text-slate-500">
          8-node agentic pipeline
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={i} className="rounded-2xl border border-slate-700/50 bg-slate-800/40 p-5 backdrop-blur-sm">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 text-sm font-bold">
                {i + 1}
              </div>
              <h3 className="mb-1.5 font-semibold text-white text-sm">{step.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <div key={i} className="flex gap-3">
              <div className="mt-0.5 flex-shrink-0 text-blue-400">{f.icon}</div>
              <div>
                <h3 className="mb-1 text-sm font-semibold text-white">{f.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 text-center text-xs text-slate-600">
        FinComplaint AI · Built on CFPB Consumer Complaint Database · UMD Academic Project
      </footer>
    </main>
  )
}

const PIPELINE_STEPS = [
  { title: 'Intake & PII Scrubbing', desc: 'Strips SSNs, card numbers, phone and email addresses before any AI processing.' },
  { title: 'Classification', desc: 'Classifies by product type, issue type, severity, and compliance risk with confidence scoring.' },
  { title: 'Routing', desc: 'Auto-routes based on confidence and risk level; flags high-risk cases for human review.' },
  { title: 'Root Cause Analysis', desc: 'Retrieves 5 similar historical complaints via vector RAG to ground the diagnosis.' },
  { title: 'Remediation Planning', desc: 'Generates an ordered action plan grounded in MCP policy server SLA requirements.' },
  { title: 'Response Drafting', desc: 'Writes a regulatory-compliant customer response letter citing applicable regulations.' },
  { title: 'Compliance Audit', desc: 'Audits the response draft in a loop, requesting rewrites until PASS verdict is reached.' },
  { title: 'Explanation', desc: 'Produces a full decision-chain explanation suitable for CFPB regulatory review.' },
]

const FEATURES = [
  { icon: <Shield className="h-5 w-5" />, title: 'Production Security', desc: 'JWT RS256, bcrypt, CSRF, rate limiting, account lockout, security headers, audit logging.' },
  { icon: <Search className="h-5 w-5" />, title: 'Vector RAG', desc: 'ChromaDB with bge-large-en-v1.5 embeddings over 5,000+ CFPB complaint records.' },
  { icon: <FileText className="h-5 w-5" />, title: 'CFPB Aligned', desc: 'Classification taxonomy and SLA windows aligned to CFPB complaint categories and Regulation E/Z.' },
  { icon: <CheckCircle className="h-5 w-5" />, title: 'Compliance Audited', desc: 'Every response is audited in a loop before delivery. Fail codes are corrected automatically.' },
  { icon: <BarChart3 className="h-5 w-5" />, title: 'Full Observability', desc: 'Node-level audit trail, token usage, latency tracking, and real-time WebSocket pipeline view.' },
  { icon: <Zap className="h-5 w-5" />, title: 'Real-time', desc: 'WebSocket-driven pipeline view updates live as each agent node completes.' },
]
