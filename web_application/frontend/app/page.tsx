import Link from 'next/link'
import {
  Shield, Zap, Search, FileText, CheckCircle, BarChart3,
  ArrowRight, Lock, Database, Bot,
} from 'lucide-react'

export const metadata = {
  title: 'FinComplaint AI — Financial Complaint Triage',
  description: 'AI-powered complaint triage, classification, and remediation for financial services.',
}

/* ── Pipeline node data ──────────────────────────────────────────────────── */
const PIPELINE_STEPS = [
  { n: '01', title: 'Intake & PII Scrubbing',   desc: 'Strips SSNs, card numbers, phone & email addresses before any AI processing.' },
  { n: '02', title: 'Complaint Classification', desc: 'Classifies by product type, issue type, severity, and compliance risk with confidence scoring.' },
  { n: '03', title: 'Routing Decision',         desc: 'Auto-routes based on risk level; flags high-confidence cases for human review.' },
  { n: '04', title: 'Root Cause Analysis',      desc: 'Retrieves 5 similar historical complaints via vector RAG to ground the diagnosis.' },
  { n: '05', title: 'Remediation Planning',     desc: 'Generates an ordered action plan grounded in MCP policy server SLA requirements.' },
  { n: '06', title: 'Response Drafting',        desc: 'Writes a regulatory-compliant customer response letter citing applicable regulations.' },
  { n: '07', title: 'Compliance Audit',         desc: 'Audits the response draft in a loop, requesting rewrites until PASS verdict is reached.' },
  { n: '08', title: 'Explanation Chain',        desc: 'Produces a full decision chain explanation suitable for CFPB regulatory review.' },
]

const FEATURES = [
  { icon: Lock,       title: 'Production Security',    desc: 'JWT RS256, bcrypt, CSRF tokens, rate limiting, account lockout, full audit logging.' },
  { icon: Search,     title: 'Vector RAG',             desc: 'ChromaDB with bge-large-en-v1.5 over 5,000+ CFPB complaint records.' },
  { icon: FileText,   title: 'CFPB Aligned',           desc: 'Taxonomy aligned to CFPB categories, Regulation E, Regulation Z, and FCRA.' },
  { icon: CheckCircle,title: 'Compliance Audited',     desc: 'Every response audited in a loop before delivery. Fail codes auto-corrected.' },
  { icon: BarChart3,  title: 'Full Observability',     desc: 'Node-level audit trail, token counts, latency, and live WebSocket pipeline view.' },
  { icon: Bot,        title: 'Agentic Pipeline',       desc: '8-node async pipeline with human-in-the-loop at the routing decision node.' },
]

const TECH = [
  { label: 'Groq LPU',     tag: 'LLM Inference' },
  { label: 'ChromaDB',     tag: 'Vector Store' },
  { label: 'MongoDB Atlas', tag: 'Document DB' },
  { label: 'FastAPI',      tag: 'REST + WebSocket' },
  { label: 'Next.js 14',   tag: 'App Router' },
  { label: 'Redis',        tag: 'Session Cache' },
]

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-background">

      {/* ── Background effects ───────────────────────────────── */}
      <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-100" />
      {/* Giant orb — centered above hero */}
      <div
        className="pointer-events-none absolute left-1/2 top-[-10%] h-[700px] w-[700px] -translate-x-1/2 rounded-full animate-orb-breathe"
        style={{
          background: 'radial-gradient(circle at center, rgba(99,102,241,0.18) 0%, rgba(99,102,241,0.06) 40%, transparent 70%)',
          filter: 'blur(40px)',
        }}
      />
      <div
        className="pointer-events-none absolute left-[60%] top-[30%] h-[400px] w-[400px] rounded-full"
        style={{
          background: 'radial-gradient(circle at center, rgba(139,92,246,0.1) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />

      {/* ── Nav ─────────────────────────────────────────────── */}
      <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/15 border border-primary/25">
            <Shield className="h-4 w-4 text-primary" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-semibold text-foreground">FinComplaint</span>
            <span className="text-[9px] font-bold uppercase tracking-[0.14em] text-gradient-indigo">AI Platform</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Sign in
          </Link>
          <Link href="/register" className="btn-primary py-2">
            Get started <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 pt-24 pb-20 text-center">
        {/* Tag pill */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-4 py-1.5">
          <Zap className="h-3 w-3 text-primary" />
          <span className="text-xs font-semibold text-indigo-300">Groq LPU · ChromaDB · MongoDB Atlas</span>
        </div>

        {/* Main headline */}
        <h1 className="mb-6 font-serif text-6xl font-normal leading-[1.05] tracking-tight sm:text-7xl">
          <span className="text-gradient-white">Financial Complaint</span>
          <br />
          <span className="text-gradient-indigo italic">Intelligence</span>
        </h1>

        {/* Subheadline */}
        <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground leading-relaxed">
          8-node agentic pipeline that classifies, routes, analyzes root cause,
          generates policy-grounded remediation, and drafts regulatory-compliant
          responses — with full explainability for CFPB oversight.
        </p>

        {/* CTA row */}
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link href="/register" className="btn-primary px-8 py-3 text-base">
            Start triaging <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/login" className="btn-outline px-8 py-3 text-base">
            Sign in to dashboard
          </Link>
        </div>

        {/* Tech stack pills */}
        <div className="mt-12 flex flex-wrap justify-center gap-2">
          {TECH.map((t) => (
            <div key={t.label}
              className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1">
              <span className="text-xs font-semibold text-foreground/80">{t.label}</span>
              <span className="text-[10px] text-muted-foreground">{t.tag}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pipeline track ───────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-7xl px-6 py-20">
        <div className="mb-12 text-center">
          <p className="section-label mb-3">8-node agentic pipeline</p>
          <h2 className="font-serif text-3xl text-foreground">How it works</h2>
        </div>

        {/* Horizontal scrolling step cards */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE_STEPS.map((step, i) => (
            <div
              key={i}
              className="glass-card p-5 group hover:border-primary/20 hover:-translate-y-0.5 transition-all duration-300"
            >
              <div className="mb-4 flex items-center justify-between">
                <span className="font-mono text-[11px] font-bold text-primary/60 tracking-widest">{step.n}</span>
                {/* Connector dots */}
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className="hidden lg:flex items-center gap-0.5">
                    {[0,1,2].map(d => (
                      <div key={d} className="h-1 w-1 rounded-full bg-white/10" />
                    ))}
                  </div>
                )}
              </div>
              <h3 className="mb-2 text-sm font-semibold text-foreground group-hover:text-primary/90 transition-colors">
                {step.title}
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-5xl px-6 py-16">
        <div className="mb-12 text-center">
          <p className="section-label mb-3">Built for production</p>
          <h2 className="font-serif text-3xl text-foreground">Enterprise grade, from day one</h2>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <div key={i} className="flex gap-4 rounded-2xl border border-white/[0.05] bg-white/[0.02] p-5 hover:border-white/[0.09] transition-colors duration-200">
              <div className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
                <f.icon className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h3 className="mb-1.5 text-sm font-semibold text-foreground">{f.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA banner ───────────────────────────────────────── */}
      <section className="relative z-10 mx-auto max-w-3xl px-6 py-20 text-center">
        <div className="rounded-3xl border border-primary/20 bg-primary/[0.06] p-12"
          style={{ boxShadow: '0 0 80px rgba(99,102,241,0.12) inset' }}>
          <h2 className="mb-4 font-serif text-4xl text-foreground">
            Ready to modernize complaint triage?
          </h2>
          <p className="mb-8 text-muted-foreground leading-relaxed">
            Deploy the full 8-node pipeline in minutes. CFPB-aligned taxonomy,
            production security, and real-time observability included.
          </p>
          <Link href="/register" className="btn-primary px-10 py-3.5 text-base">
            Get started free <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/[0.05] py-8 text-center">
        <p className="text-xs text-muted-foreground/50">
          FinComplaint AI &nbsp;·&nbsp; Built on CFPB Consumer Complaint Database &nbsp;·&nbsp; UMD Academic Project
        </p>
      </footer>
    </main>
  )
}
