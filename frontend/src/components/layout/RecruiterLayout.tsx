import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, Users, MessageSquare, User,
  LogOut, Zap,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { cn, initials } from '@/lib/utils'
import NotificationBell from '@/components/NotificationBell'

const NAV = [
  { to: '/dashboard',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/dashboard/jobs',       icon: Briefcase,       label: 'Jobs' },
  { to: '/dashboard/candidates', icon: Users,           label: 'Candidates' },
  { to: '/dashboard/messages',   icon: MessageSquare,   label: 'Messages' },
  { to: '/dashboard/profile',    icon: User,            label: 'Profile' },
]

export default function RecruiterLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-100">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-lg">Shortlist AI</span>
          </button>
          <p className="text-xs text-gray-500 mt-1 ml-10">Recruiter Portal</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/dashboard'}
              className={({ isActive }) => cn('sidebar-link', isActive && 'active')}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-3 py-4 border-t border-gray-100">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold shrink-0">
              {initials(user?.full_name || 'R')}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 truncate">
                {user?.recruiter?.company_name || user?.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-1 w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* ── Main area ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-end gap-3 shrink-0">
          <NotificationBell pollInterval={10_000} />
        </header>

        {/* Scrollable page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {children}
        </main>
      </div>

    </div>
  )
}
