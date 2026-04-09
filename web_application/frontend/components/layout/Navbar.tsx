'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth'
import { Shield, LogOut, LayoutDashboard, FileText, Settings } from 'lucide-react'

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore()
  const router = useRouter()

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  if (!isAuthenticated) return null

  return (
    <header className="sticky top-0 z-50 h-16 border-b border-slate-200 bg-white/90 backdrop-blur-sm">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <Link href="/dashboard" className="flex items-center gap-2.5 font-bold text-slate-900">
          <Shield className="h-5 w-5 text-blue-600" />
          <span>FinComplaint AI</span>
        </Link>

        {/* Nav links */}
        <nav className="hidden items-center gap-1 sm:flex">
          <NavLink href="/dashboard" icon={<LayoutDashboard className="h-4 w-4" />}>
            Dashboard
          </NavLink>
          <NavLink href="/complaints" icon={<FileText className="h-4 w-4" />}>
            Complaints
          </NavLink>
          {user?.role === 'admin' && (
            <NavLink href="/admin" icon={<Settings className="h-4 w-4" />}>
              Admin
            </NavLink>
          )}
        </nav>

        {/* User */}
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-slate-600 sm:block">
            {user?.full_name}
            <span className="ml-1.5 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
              {user?.role}
            </span>
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:block">Sign out</span>
          </button>
        </div>
      </div>
    </header>
  )
}

function NavLink({ href, icon, children }: { href: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
    >
      {icon}
      {children}
    </Link>
  )
}
