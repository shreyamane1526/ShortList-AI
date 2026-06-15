/**
 * Breadcrumb — persistent navigation trail for candidate pages.
 * Reads the current route and renders a semantic breadcrumb.
 */
import { Link, useLocation } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'

const ROUTE_LABELS: Record<string, string> = {
  '/candidate':              'Dashboard',
  '/candidate/jobs':         'Job Feed',
  '/candidate/applications': 'My Applications',
  '/candidate/learning-hub': 'Learning Hub',
  '/candidate/messages':     'Messages',
  '/candidate/profile':      'Profile',
  '/candidate/onboarding':   'Setup Profile',
}

interface Crumb {
  label: string
  to?: string
}

export default function Breadcrumb() {
  const { pathname } = useLocation()

  const crumbs: Crumb[] = [{ label: 'Dashboard', to: '/candidate' }]

  if (pathname !== '/candidate') {
    const label = ROUTE_LABELS[pathname]
    if (label) {
      crumbs.push({ label })
    }
  }

  if (crumbs.length <= 1 && pathname === '/candidate') {
    // On dashboard itself — just show "Dashboard" as current
    return (
      <nav aria-label="Breadcrumb" className="nd-breadcrumb">
        <Home className="w-3 h-3" aria-hidden="true" />
        <span className="current">Dashboard</span>
      </nav>
    )
  }

  return (
    <nav aria-label="Breadcrumb" className="nd-breadcrumb">
      <Home className="w-3 h-3" aria-hidden="true" />
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1
        return (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="w-3 h-3 opacity-40" aria-hidden="true" />}
            {isLast || !crumb.to ? (
              <span className="current" aria-current={isLast ? 'page' : undefined}>
                {crumb.label}
              </span>
            ) : (
              <Link to={crumb.to}>{crumb.label}</Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}
