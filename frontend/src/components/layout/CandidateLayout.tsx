import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, FileText, MessageSquare, User,
  LogOut, Zap, BookOpen,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { cn, initials } from '@/lib/utils'
import NotificationBell from '@/components/NotificationBell'
import AccessibilityToolbar from '@/components/accessibility/AccessibilityToolbar'
import ReadingRuler from '@/components/accessibility/ReadingRuler'
import Breadcrumb from '@/components/accessibility/Breadcrumb'

// All nav items include text labels — no icon-only buttons
const NAV = [
  { to: '/candidate',              icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/candidate/jobs',         icon: Briefcase,       label: 'Job Feed' },
  { to: '/candidate/applications', icon: FileText,        label: 'Applications' },
  { to: '/candidate/learning-hub', icon: BookOpen,        label: 'Learning Hub' },
  { to: '/candidate/messages',     icon: MessageSquare,   label: 'Messages' },
  { to: '/candidate/profile',      icon: User,            label: 'Profile' },
]

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--nd-bg, #F9FAFB)' }}>

      {/* ── Skip to main content (screen reader + keyboard) ─────────────── */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[9999] focus:px-4 focus:py-2 focus:bg-yellow-300 focus:text-black focus:rounded-lg focus:font-semibold focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside
        className="w-64 border-r flex flex-col shrink-0"
        style={{ backgroundColor: 'var(--nd-card-bg, #fff)', borderColor: 'rgba(0,0,0,0.08)' }}
        aria-label="Candidate navigation"
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b" style={{ borderColor: 'rgba(0,0,0,0.06)' }}>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            aria-label="Shortlist AI — go to home"
          >
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center" aria-hidden="true">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg" style={{ color: 'var(--nd-text, #111827)' }}>
              Shortlist AI
            </span>
          </button>
          <p className="text-xs mt-1 ml-10" style={{ color: 'var(--nd-muted, #6B7280)' }}>
            Candidate Portal
          </p>
        </div>

        {/* Nav — all items have visible text labels */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto" aria-label="Main navigation">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/candidate'}
              className={({ isActive }) => cn('sidebar-link', isActive && 'active')}
              aria-label={label}
            >
              <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="px-3 py-4 border-t" style={{ borderColor: 'rgba(0,0,0,0.06)' }}>
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ backgroundColor: 'var(--nd-focus-bg, #4F46E5)', color: '#fff' }}
              aria-hidden="true"
            >
              {initials(user?.full_name || 'U')}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--nd-text, #111827)' }}>
                {user?.full_name}
              </p>
              <p className="text-xs truncate" style={{ color: 'var(--nd-muted, #6B7280)' }}>
                {user?.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-1 w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors hover:bg-red-50 hover:text-red-600"
            style={{ color: 'var(--nd-muted, #6B7280)' }}
            aria-label="Sign out of your account"
          >
            <LogOut className="w-4 h-4" aria-hidden="true" />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* ── Main area ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header
          className="border-b px-6 py-3 flex items-center justify-end gap-3 shrink-0"
          style={{ backgroundColor: 'var(--nd-card-bg, #fff)', borderColor: 'rgba(0,0,0,0.08)' }}
          aria-label="Top navigation bar"
        >
          <NotificationBell pollInterval={10_000} />
        </header>

        {/* Scrollable page content */}
        <main
          id="main-content"
          className="flex-1 overflow-y-auto px-6 py-6"
          style={{ backgroundColor: 'var(--nd-bg, #F9FAFB)' }}
          tabIndex={-1}
        >
          {/* Persistent breadcrumb trail */}
          <Breadcrumb />

          {children}

          {/* Global accessibility toolbar + reading ruler (candidate-only) */}
          <AccessibilityToolbar />
          <ReadingRuler />
        </main>
      </div>

    </div>
  )
}
