'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Loader2, Send, Sparkles, Info, ChevronDown } from 'lucide-react'
import Link from 'next/link'
import Navbar from '@/components/layout/Navbar'
import { useAuthStore } from '@/store/auth'
import { useComplaintsStore } from '@/store/complaints'

/* ── US states ───────────────────────────────────────────────────────────── */
const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY',
]

/* ── Form schema ─────────────────────────────────────────────────────────── */
const schema = z.object({
  complaint_text: z
    .string()
    .min(20, 'Please provide at least 20 characters')
    .max(10_000, 'Maximum 10,000 characters'),
  state_code: z.string().length(2, 'Select a state'),
})
type FormData = z.infer<typeof schema>

/* ── Demo presets ────────────────────────────────────────────────────────── */
const DEMO_COMPLAINTS = [
  {
    label: 'Billing Error',
    badge: 'MEDIUM',
    text: 'I was charged twice on my credit card for a purchase I made on April 5th totaling $150. I have already filed a dispute with my bank but have not received any written acknowledgment or update on the investigation status. This is the third time this has happened in the past six months.',
  },
  {
    label: 'Fraud / Unauthorized',
    badge: 'HIGH',
    text: 'I noticed three unauthorized charges on my debit account totaling $847 that I did not authorize. The transactions appear to have originated from an overseas merchant. I contacted customer service and was placed on hold for over 45 minutes before being disconnected. I need these charges reversed immediately and my account secured.',
  },
  {
    label: 'Identity Theft',
    badge: 'CRITICAL',
    text: 'Someone has opened a credit card account in my name without my authorization. I discovered this when I pulled my credit report and found an account I never applied for. The account has already accumulated $2,300 in charges. I need this account frozen immediately and removed from my credit report.',
  },
]

const BADGE_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-500/15 text-red-400 border-red-500/25',
  HIGH:     'bg-orange-500/15 text-orange-400 border-orange-500/25',
  MEDIUM:   'bg-amber-500/15 text-amber-400 border-amber-500/25',
}

/* ── Pipeline steps ──────────────────────────────────────────────────────── */
const PIPELINE_STEPS = [
  'PII is automatically scrubbed from your text',
  'AI classifies by product, issue type, severity & risk',
  'Root cause identified via historical complaint matching',
  'Policy-grounded remediation plan is generated',
  'Regulatory-compliant response letter is drafted & audited',
  'Full explanation chain produced for regulator review',
]

export default function NewComplaintPage() {
  const router  = useRouter()
  const { isAuthenticated, loadUser } = useAuthStore()
  const { submitComplaint } = useComplaintsStore()
  const [submitting, setSubmitting]   = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { state_code: 'CA' },
  })

  const textValue = watch('complaint_text') ?? ''

  useEffect(() => {
    if (!isAuthenticated)
      loadUser().then(() => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
  }, [])

  const onSubmit = async (data: FormData) => {
    setSubmitting(true)
    setServerError(null)
    try {
      const id = await submitComplaint(data.complaint_text, data.state_code)
      router.push(`/complaints/${id}`)
    } catch (e: any) {
      setServerError(e.response?.data?.detail ?? 'Submission failed. Please try again.')
      setSubmitting(false)
    }
  }

  const charPct = (textValue.length / 10_000) * 100

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">

        {/* ── Back + heading ────────────────────────────────── */}
        <div className="mb-6 flex items-center gap-3 animate-fade-up">
          <Link href="/complaints" className="btn-ghost gap-1.5 px-2 py-1.5 text-sm">
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <span className="text-white/10">/</span>
          <h1 className="font-serif text-xl text-foreground">Submit Complaint</h1>
        </div>

        {/* ── Quick presets ──────────────────────────────────── */}
        <div className="mb-6 animate-fade-up delay-75">
          <div className="mb-2.5 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <p className="section-label">Quick presets</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {DEMO_COMPLAINTS.map((d) => (
              <button
                key={d.label}
                type="button"
                onClick={() => setValue('complaint_text', d.text, { shouldValidate: true })}
                className="group flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 transition-all duration-200 hover:border-primary/30 hover:bg-primary/[0.07]"
              >
                <span className="text-xs font-medium text-foreground/80 group-hover:text-foreground">
                  {d.label}
                </span>
                <span className={`rounded-full border px-1.5 py-0.5 text-[9px] font-bold tracking-wide ${BADGE_COLORS[d.badge]}`}>
                  {d.badge}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* ── Form ──────────────────────────────────────────── */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="glass-card p-7 space-y-6 animate-fade-up delay-150"
          noValidate
        >
          {serverError && (
            <div className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {serverError}
            </div>
          )}

          {/* ── Complaint text ── */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-semibold text-foreground/70 uppercase tracking-wider">
                Complaint Description <span className="text-primary">*</span>
              </label>
              <span className={`font-mono text-[10px] transition-colors ${
                textValue.length > 9500 ? 'text-red-400' : 'text-muted-foreground/60'
              }`}>
                {textValue.length.toLocaleString()} / 10,000
              </span>
            </div>

            <textarea
              {...register('complaint_text')}
              rows={8}
              placeholder="Describe your financial complaint in detail. Include relevant dates, amounts, product types, and any actions you've already taken. Personal information (SSN, card numbers, emails, phone numbers) will be automatically redacted."
              className="field resize-y leading-relaxed"
            />

            {/* Progress bar */}
            <div className="mt-2 h-0.5 rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  charPct > 95 ? 'bg-red-500' : charPct > 80 ? 'bg-amber-500' : 'bg-primary/60'
                }`}
                style={{ width: `${Math.min(charPct, 100)}%` }}
              />
            </div>

            {errors.complaint_text ? (
              <p className="mt-1.5 text-xs text-red-400">{errors.complaint_text.message}</p>
            ) : (
              <p className="mt-1.5 text-[11px] text-muted-foreground/50">
                PII (SSN, card numbers, emails, phone numbers) will be automatically redacted.
              </p>
            )}
          </div>

          {/* ── State select ── */}
          <div>
            <label className="mb-2 block text-xs font-semibold text-foreground/70 uppercase tracking-wider">
              State <span className="text-primary">*</span>
            </label>
            <div className="relative">
              <select
                {...register('state_code')}
                className="field appearance-none pr-9"
              >
                {US_STATES.map((s) => (
                  <option key={s} value={s} className="bg-card">{s}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
            {errors.state_code && (
              <p className="mt-1.5 text-xs text-red-400">{errors.state_code.message}</p>
            )}
          </div>

          {/* ── What happens next ── */}
          <div className="rounded-xl border border-primary/15 bg-primary/[0.05] p-4">
            <div className="mb-2.5 flex items-center gap-2">
              <Info className="h-3.5 w-3.5 text-primary/70" />
              <p className="text-xs font-semibold text-foreground/70">What happens after submission</p>
            </div>
            <ol className="space-y-1.5">
              {PIPELINE_STEPS.map((step, i) => (
                <li key={i} className="flex items-start gap-2.5 text-xs text-muted-foreground">
                  <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 font-mono text-[9px] font-bold text-primary">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          {/* ── Submit ── */}
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full py-3 text-sm"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Processing submission…</>
            ) : (
              <><Send className="h-4 w-4" /> Submit Complaint</>
            )}
          </button>
        </form>
      </main>
    </div>
  )
}
