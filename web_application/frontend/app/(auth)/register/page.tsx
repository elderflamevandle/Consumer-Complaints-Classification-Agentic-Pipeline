'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Link from 'next/link'
import { Shield, Loader2, ArrowRight, User, Mail, Lock, Eye } from 'lucide-react'
import { useAuthStore } from '@/store/auth'

/* ── Password policy mirrors backend ────────────────────────────────────── */
const passwordSchema = z
  .string()
  .min(8, 'At least 8 characters')
  .regex(/[A-Z]/, 'Must include an uppercase letter')
  .regex(/[a-z]/, 'Must include a lowercase letter')
  .regex(/\d/, 'Must include a digit')
  .regex(/[!@#$%^&*()\-_=+\[\]{};':"\\|,.<>/?]/, 'Must include a special character')

const schema = z.object({
  full_name: z.string().min(1, 'Full name required').max(120),
  email:     z.string().email('Invalid email address'),
  password:  passwordSchema,
  confirm:   z.string(),
}).refine((d) => d.password === d.confirm, {
  message: 'Passwords do not match',
  path: ['confirm'],
})
type FormData = z.infer<typeof schema>

export default function RegisterPage() {
  const router = useRouter()
  const { register: registerUser, isAuthenticated, isLoading, error, clearError } = useAuthStore()

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  useEffect(() => { if (isAuthenticated) router.push('/dashboard') }, [isAuthenticated])
  useEffect(() => { return clearError }, [])

  const onSubmit = async (data: FormData) => {
    try { await registerUser(data.email, data.password, data.full_name) }
    catch { /* error shown from store */ }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4">
      {/* Background */}
      <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-60" />
      <div
        className="pointer-events-none absolute top-[-15%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full animate-orb-breathe"
        style={{
          background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 45%, transparent 70%)',
          filter: 'blur(50px)',
        }}
      />

      <div className="relative z-10 w-full max-w-sm animate-fade-up">
        {/* Logo */}
        <div className="mb-8 text-center">
          <Link href="/" className="inline-flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 border border-primary/25"
              style={{ boxShadow: '0 0 32px rgba(99,102,241,0.2)' }}>
              <Shield className="h-7 w-7 text-primary" />
            </div>
            <div>
              <p className="font-serif text-2xl text-foreground">FinComplaint AI</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Create your account</p>
            </div>
          </Link>
        </div>

        {/* Card */}
        <div className="glass-card p-8" style={{ boxShadow: '0 24px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)' }}>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {error && (
              <div className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <FormField label="Full Name" error={errors.full_name?.message}>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
                <input
                  {...register('full_name')}
                  type="text"
                  autoComplete="name"
                  placeholder="Jane Smith"
                  className="field pl-9"
                />
              </div>
            </FormField>

            <FormField label="Email" error={errors.email?.message}>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  className="field pl-9"
                />
              </div>
            </FormField>

            <FormField label="Password" error={errors.password?.message}>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
                <input
                  {...register('password')}
                  type="password"
                  autoComplete="new-password"
                  placeholder="Min 8 chars, upper, digit, special"
                  className="field pl-9"
                />
              </div>
            </FormField>

            <FormField label="Confirm Password" error={errors.confirm?.message}>
              <div className="relative">
                <Eye className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
                <input
                  {...register('confirm')}
                  type="password"
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className="field pl-9"
                />
              </div>
            </FormField>

            {/* Password hint */}
            <p className="text-[11px] text-muted-foreground/50 leading-relaxed">
              Password must be 8+ chars with at least one uppercase, lowercase, digit, and special character.
            </p>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3 mt-2"
            >
              {isLoading ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Creating account…</>
              ) : (
                <>Create account <ArrowRight className="h-3.5 w-3.5" /></>
              )}
            </button>
          </form>

          <div className="mt-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/[0.06]" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="flex-1 h-px bg-white/[0.06]" />
          </div>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold text-primary hover:text-indigo-300 transition-colors">
              Sign in
            </Link>
          </p>
        </div>

        <p className="mt-6 text-center text-[11px] text-muted-foreground/40">
          Protected by JWT RS256 · bcrypt · Rate limiting
        </p>
      </div>
    </div>
  )
}

function FormField({
  label, error, children,
}: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-foreground/60">
        {label}
      </label>
      {children}
      {error && <p className="mt-1.5 text-xs text-red-400">{error}</p>}
    </div>
  )
}
