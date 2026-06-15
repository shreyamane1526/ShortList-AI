import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom'
import { useEffect } from 'react'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { NDPreferencesProvider } from '@/context/NDPreferencesContext'

// Pages
import { LandingPage } from '@/pages/landing'
import AuthPage from '@/pages/AuthPage'
import AdminDashboard from '@/pages/admin/Dashboard'
import CandidateDashboard from '@/pages/candidate/Dashboard'
import CandidateOnboarding from '@/pages/candidate/Onboarding'
import CandidateJobs from '@/pages/candidate/Jobs'
import CandidateApplications from '@/pages/candidate/Applications'
import CandidateLearningHub from '@/pages/candidate/LearningHub'
import CandidateMessages from '@/pages/candidate/Messages'
import CandidateProfile from '@/pages/candidate/Profile'
import RecruiterDashboard from '@/pages/recruiter/Dashboard'
import RecruiterJobs from '@/pages/recruiter/Jobs'
import RecruiterCandidates from '@/pages/recruiter/Candidates'
import RecruiterMessages from '@/pages/recruiter/Messages'
import RecruiterProfile from '@/pages/recruiter/Profile'

// ── Spinner shown during auth loading ─────────────────────────────────────────
function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

// ── OAuth callback — reads ?token=&role= from Google/LinkedIn redirect ─────────
function OAuthCallback() {
  const [params] = useSearchParams()
  const { refreshUser } = useAuth()

  useEffect(() => {
    const token = params.get('token')
    const status = params.get('status')
    const role = params.get('role')
    if (status === 'success' && token) {
      localStorage.setItem('access_token', token)
      refreshUser().then(() => {
        window.location.href = role === 'superadmin'
          ? '/admin'
          : role === 'recruiter'
            ? '/dashboard'
            : '/candidate'
      })
    }
  }, [params, refreshUser])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-gray-600 text-sm">Signing you in…</p>
      </div>
    </div>
  )
}

// ── Route guard ────────────────────────────────────────────────────────────────
function RequireAuth({
  children,
  role,
}: {
  children: React.ReactNode
  role?: 'candidate' | 'recruiter' | 'superadmin'
}) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/auth" replace />
  if (role && user.role !== role) {
    if (user.role === 'superadmin') return <Navigate to="/admin" replace />
    return <Navigate to={user.role === 'recruiter' ? '/dashboard' : '/candidate'} replace />
  }
  return <>{children}</>
}

// ── Root: landing for guests, dashboard redirect for logged-in users ───────────
function RootRoute() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (user) {
    if (user.role === 'superadmin') return <Navigate to="/admin" replace />
    return <Navigate to={user.role === 'recruiter' ? '/dashboard' : '/candidate'} replace />
  }
  return <LandingPage />
}

// ── Candidate section — all wrapped in a single NDPreferencesProvider ──────────
// This ensures preferences persist across navigation without re-mounting the provider.
function CandidateSection() {
  return (
    <RequireAuth role="candidate">
      <NDPreferencesProvider>
        <Routes>
          <Route index element={<CandidateDashboard />} />
          <Route path="onboarding" element={<CandidateOnboarding />} />
          <Route path="jobs" element={<CandidateJobs />} />
          <Route path="applications" element={<CandidateApplications />} />
          <Route path="learning-hub" element={<CandidateLearningHub />} />
          <Route path="messages" element={<CandidateMessages />} />
          <Route path="profile" element={<CandidateProfile />} />
        </Routes>
      </NDPreferencesProvider>
    </RequireAuth>
  )
}

// ── App ────────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/"               element={<RootRoute />} />
        <Route path="/auth"           element={<AuthPage />} />
        <Route path="/oauth/callback" element={<OAuthCallback />} />

        {/* Superadmin */}
        <Route path="/admin"   element={<RequireAuth role="superadmin"><AdminDashboard /></RequireAuth>} />
        <Route path="/admin/*" element={<RequireAuth role="superadmin"><AdminDashboard /></RequireAuth>} />

        {/* Candidate — single NDPreferencesProvider wraps all candidate routes */}
        <Route path="/candidate/*" element={<CandidateSection />} />

        {/* Recruiter */}
        <Route path="/dashboard"            element={<RequireAuth role="recruiter"><RecruiterDashboard /></RequireAuth>} />
        <Route path="/dashboard/jobs"       element={<RequireAuth role="recruiter"><RecruiterJobs /></RequireAuth>} />
        <Route path="/dashboard/candidates" element={<RequireAuth role="recruiter"><RecruiterCandidates /></RequireAuth>} />
        <Route path="/dashboard/messages"   element={<RequireAuth role="recruiter"><RecruiterMessages /></RequireAuth>} />
        <Route path="/dashboard/profile"    element={<RequireAuth role="recruiter"><RecruiterProfile /></RequireAuth>} />

        {/* Catch-all */}
        <Route path="*" element={<RootRoute />} />
      </Routes>
    </AuthProvider>
  )
}
