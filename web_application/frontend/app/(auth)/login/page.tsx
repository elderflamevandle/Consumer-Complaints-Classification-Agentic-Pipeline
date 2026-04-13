'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Link from 'next/link'
import { Shield, Loader2, ArrowRight, Lock, Mail } from 'lucide-react'
import { useAuthStore } from '@/store/auth'

const schema = z.object({
  email:    z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const router = useRouter()
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore()

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  useEffect(() => { if (isAuthenticated) router.push('/dashboard') }, [isAuthenticated])
  useEffect(() => { return clearError }, [])

  const onSubmit = async (data: FormData) => {
    try { await login(data.email, data.password) }
    catch { /* error shown from store */ }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4">

      {/* ── Background orb ────────────────────────────────── */}
      <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-60" />
      <div
        className="pointer-events-none absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full animate-orb-breathe"
        style={{
          background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, rgba(99,102,241,0.05) 45%, transparent 70%)',
          filter: 'blur(50px)',
        }}
      />

      <div className="relative z-10 w-full max-w-sm animate-fade-up">

        {/* ── Logo ────────────────────────────────────────── */}
        <div className="mb-10 text-center">
          <Link href="/" className="inline-flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 border border-primary/25"
              style={{ boxShadow: '0 0 32px rgba(99,102,241,0.2)' }}>
              <Shield className="h-7 w-7 text-primary" />
            </div>
            <div>
              <p className="font-serif text-2xl text-foreground">FinComplaint AI</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Financial Compliance Platform</p>
            </div>
          </Link>
        </div>

        {/* ── Card ────────────────────────────────────────── */}
        <div className="glass-card p-8" style={{ boxShadow: '0 24px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)' }}>
          <h1 className="mb-6 text-center text-lg font-semibold text-foreground">
            Sign in to your account
          </h1>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {/* Global error */}
            {error && (
              <div className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Email */}
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-foreground/60">
                Email
              </label>
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
              {errors.email && (
                <p className="mt-1.5 text-xs text-red-400">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-foreground/60">
                Password
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/50" />
                <input
                  {...register('password')}
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="field pl-9"
                />
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-red-400">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3"
            >
              {isLoading ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Signing in…</>
              ) : (
                <>Sign in <ArrowRight className="h-3.5 w-3.5" /></>
              )}
            </button>
          </form>

          <div className="mt-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/[0.06]" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="flex-1 h-px bg-white/[0.06]" />
          </div>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            No account?{' '}
            <Link href="/register" className="font-semibold text-primary hover:text-indigo-300 transition-colors">
              Register now
            </Link>
          </p>
        </div>

        <p className="mt-6 text-center text-[11px] text-muted-foreground/40">
          Protected by JWT RS256 · CSRF tokens · Rate limiting
        </p>
      </div>
    </div>
  )
}
