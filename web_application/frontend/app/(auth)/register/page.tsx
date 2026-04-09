'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import Link from 'next/link'
import { Shield, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/store/auth'

// Password policy mirrors backend: min 8, upper, lower, digit, special
const passwordSchema = z
  .string()
  .min(8, 'At least 8 characters')
  .regex(/[A-Z]/, 'Include at least one uppercase letter')
  .regex(/[a-z]/, 'Include at least one lowercase letter')
  .regex(/\d/, 'Include at least one digit')
  .regex(/[!@#$%^&*()\-_=+\[\]{};':"\\|,.<>/?]/, 'Include at least one special character')

const schema = z.object({
  full_name: z.string().min(1, 'Full name required').max(120),
  email: z.string().email('Invalid email'),
  password: passwordSchema,
  confirm: z.string(),
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
    try {
      await registerUser(data.email, data.password, data.full_name)
    } catch { /* error shown from store */ }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-blue-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 shadow-lg">
            <Shield className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create account</h1>
          <p className="mt-1 text-sm text-slate-400">Join FinComplaint AI</p>
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {error && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
                {error}
              </div>
            )}

            <Field label="Full name" error={errors.full_name?.message}>
              <input
                {...register('full_name')}
                type="text"
                autoComplete="name"
                placeholder="Jane Smith"
                className={inputCls}
              />
            </Field>

            <Field label="Email" error={errors.email?.message}>
              <input
                {...register('email')}
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                className={inputCls}
              />
            </Field>

            <Field label="Password" error={errors.password?.message}>
              <input
                {...register('password')}
                type="password"
                autoComplete="new-password"
                placeholder="Min 8 chars, upper, lower, digit, special"
                className={inputCls}
              />
            </Field>

            <Field label="Confirm password" error={errors.confirm?.message}>
              <input
                {...register('confirm')}
                type="password"
                autoComplete="new-password"
                placeholder="••••••••"
                className={inputCls}
              />
            </Field>

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60 transition mt-2"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold text-blue-600 hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition'

function Field({
  label, error, children,
}: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
