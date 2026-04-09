'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Loader2, Send } from 'lucide-react'
import Link from 'next/link'
import Navbar from '@/components/layout/Navbar'
import { useAuthStore } from '@/store/auth'
import { useComplaintsStore } from '@/store/complaints'

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']

const schema = z.object({
  complaint_text: z
    .string()
    .min(20, 'Please provide at least 20 characters')
    .max(10_000, 'Maximum 10,000 characters'),
  state_code: z.string().length(2, 'Select a state'),
})
type FormData = z.infer<typeof schema>

const DEMO_COMPLAINTS = [
  {
    label: 'Billing Error',
    text: 'I was charged twice on my credit card for a purchase I made on April 5th totaling $150. I have already filed a dispute with my bank but have not received any written acknowledgment or update on the investigation status. This is the third time this has happened in the past six months.',
  },
  {
    label: 'Fraud / Unauthorized Charges',
    text: 'I noticed three unauthorized charges on my debit account totaling $847 that I did not authorize. The transactions appear to have originated from an overseas merchant. I contacted customer service and was placed on hold for over 45 minutes before being disconnected. I need these charges reversed immediately and my account secured.',
  },
  {
    label: 'Identity Theft',
    text: 'Someone has opened a credit card account in my name without my authorization. I discovered this when I pulled my credit report and found an account I never applied for. The account has already accumulated $2,300 in charges. I need this account frozen immediately and removed from my credit report.',
  },
]

export default function NewComplaintPage() {
  const router = useRouter()
  const { isAuthenticated, loadUser } = useAuthStore()
  const { submitComplaint } = useComplaintsStore()
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { state_code: 'CA' },
  })

  const textValue = watch('complaint_text') ?? ''

  useEffect(() => {
    if (!isAuthenticated) loadUser().then(() => { if (!useAuthStore.getState().isAuthenticated) router.push('/login') })
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

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <Link href="/complaints" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
          <span className="text-slate-300">/</span>
          <h1 className="text-xl font-bold text-slate-900">Submit New Complaint</h1>
        </div>

        {/* Demo presets */}
        <div className="mb-6">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Quick presets</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_COMPLAINTS.map((d) => (
              <button
                key={d.label}
                type="button"
                onClick={() => setValue('complaint_text', d.text, { shouldValidate: true })}
                className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition"
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="rounded-2xl bg-white p-8 shadow-sm border border-slate-100 space-y-6">
          {serverError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {serverError}
            </div>
          )}

          {/* Complaint text */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">
              Complaint Description <span className="text-red-500">*</span>
            </label>
            <textarea
              {...register('complaint_text')}
              rows={8}
              placeholder="Describe your financial complaint in detail. Include relevant dates, amounts, product types, and any actions you've already taken. Do not include your SSN, full credit card number, or other sensitive identifiers — these will be automatically redacted."
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition resize-y"
            />
            <div className="mt-1 flex items-center justify-between">
              {errors.complaint_text ? (
                <p className="text-xs text-red-600">{errors.complaint_text.message}</p>
              ) : (
                <p className="text-xs text-slate-400">PII (SSN, card numbers, emails, phone numbers) will be automatically redacted.</p>
              )}
              <p className={`text-xs ${textValue.length > 9500 ? 'text-red-500' : 'text-slate-400'}`}>
                {textValue.length} / 10,000
              </p>
            </div>
          </div>

          {/* State */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">
              State <span className="text-red-500">*</span>
            </label>
            <select
              {...register('state_code')}
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition"
            >
              {US_STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            {errors.state_code && <p className="mt-1 text-xs text-red-600">{errors.state_code.message}</p>}
          </div>

          {/* What happens next */}
          <div className="rounded-xl bg-blue-50 border border-blue-100 p-4">
            <p className="text-xs font-semibold text-blue-800 mb-2">What happens after submission:</p>
            <ol className="space-y-1 text-xs text-blue-700 list-decimal list-inside">
              <li>PII is scrubbed from your complaint text</li>
              <li>AI classifies by product, issue type, severity &amp; compliance risk</li>
              <li>Root cause is identified via historical complaint matching</li>
              <li>A policy-grounded remediation plan is generated</li>
              <li>A regulatory-compliant response letter is drafted and audited</li>
              <li>Full explanation chain is produced for regulator review</li>
            </ol>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60 transition"
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Submitting…</>
            ) : (
              <><Send className="h-4 w-4" /> Submit Complaint</>
            )}
          </button>
        </form>
      </main>
    </div>
  )
}
