'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth'
import { Shield, LogOut, LayoutDashboard, FileText, Settings, GitBranch } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore()
  const router   = useRouter()
  const pathname = usePathname()

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  if (!isAuthenticated) return null

  const navLinks = [
    { href: '/dashboard',    label: 'Dashboard',    icon: LayoutDashboard },
    { href: '/complaints',   label: 'Complaints',   icon: FileText },
    { href: '/architecture', label: 'Architecture', icon: GitBranch },
    ...(user?.role === 'admin' ? [{ href: '/admin', label: 'Admin', icon: Settings }] : []),
  ]

  return (
    <header className="sticky top-0 z-50 h-16 border-b border-white/[0.06] bg-background/80 backdrop-blur-xl">
      {/* subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />

      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6">

        {/* ── Brand ──────────────────────────────────────────── */}
        <Link href="/dashboard" className="group flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 border border-primary/20 group-hover:bg-primary/20 transition-all duration-200">
            <Shield className="h-4 w-4 text-primary" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-semibold text-foreground tracking-tight">FinComplaint</span>
            <span className="text-[9px] font-bold uppercase tracking-[0.15em] text-gradient-indigo">AI Platform</span>
          </div>
        </Link>

        {/* ── Nav links ───────────────────────────────────────── */}
        <nav className="hidden items-center gap-1 sm:flex">
          {navLinks.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'relative flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200',
                  active
                    ? 'text-foreground bg-white/[0.07]'
                    : 'text-muted-foreground hover:text-foreground hover:bg-white/[0.04]'
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
                {active && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5 w-4 rounded-full bg-primary" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* ── User / actions ──────────────────────────────────── */}
        <div className="flex items-center gap-2">
          {/* User chip */}
          <div className="hidden sm:flex items-center gap-2.5 rounded-xl border border-white/[0.07] bg-white/[0.03] px-3 py-1.5">
            <div className="h-6 w-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
              <span className="text-[10px] font-bold text-primary uppercase">
                {user?.full_name?.charAt(0) ?? '?'}
              </span>
            </div>
            <div className="flex flex-col leading-none gap-0.5">
              <span className="text-xs font-medium text-foreground leading-none">{user?.full_name}</span>
              <span className="text-[9px] uppercase tracking-[0.12em] font-bold text-muted-foreground">{user?.role}</span>
            </div>
            {user?.team_name && (
              <>
                <div className="w-px h-4 bg-white/10" />
                <span className="text-[10px] text-muted-foreground">{user.team_name}</span>
              </>
            )}
          </div>

          <button
            onClick={handleLogout}
            className="btn-ghost px-3 py-2 rounded-lg"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:block text-xs">Sign out</span>
          </button>
        </div>
      </div>
    </header>
  )
}
