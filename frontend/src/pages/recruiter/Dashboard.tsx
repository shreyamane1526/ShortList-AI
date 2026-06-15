import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Briefcase, Users, TrendingUp, CheckCircle2,
  RefreshCw, Plus, ChevronDown, ChevronUp, Zap,
  MessageSquare, ArrowRight, Clock3,
} from 'lucide-react'
import RecruiterLayout from '@/components/layout/RecruiterLayout'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import { cn, timeAgo, scoreBg, recommendationBadge } from '@/lib/utils'
import { EvalTrendChart, PipelineDonut } from '@/components/recruiter/TrendChart'
import type { Job, Evaluation, Application } from '@/types'

// ── KPI card ──────────────────────────────────────────────────────────────────
interface KpiProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  gradient: string
  loading?: boolean
}

function KpiCard({ label, value, sub, icon, gradient, loading }: KpiProps) {
  if (loading) return <div className="animate-pulse h-24 bg-gray-100 rounded-xl" />
  return (
    <div className={cn('rounded-xl p-4 text-white shadow-sm', gradient)}>
      <div className="flex items-start justify-between mb-2">
        <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold leading-none">{value}</p>
      <p className="text-xs text-white/80 mt-1">{label}</p>
      {sub && <p className="text-[10px] text-white/60 mt-0.5">{sub}</p>}
    </div>
  )
}

// ── Collapsible section ───────────────────────────────────────────────────────
function Section({
  title, action, actionLabel, children, defaultOpen = true,
}: {
  title: string
  action?: () => void
  actionLabel?: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
      >
        <span className="font-semibold text-gray-900 text-sm">{title}</span>
        <div className="flex items-center gap-3">
          {action && actionLabel && (
            <span
              onClick={e => { e.stopPropagation(); action() }}
              className="text-xs text-brand-600 hover:underline"
            >
              {actionLabel}
            </span>
          )}
          {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function RecruiterDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [jobs, setJobs] = useState<Job[]>([])
  const [allEvals, setAllEvals] = useState<Evaluation[]>([])
  const [allApplications, setAllApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const r = await api.get('/jobs')
        if (!cancelled) setJobs(r.data.jobs)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    const intervalId = window.setInterval(load, 15000)
    const onFocus = () => { load() }
    window.addEventListener('focus', onFocus)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
      window.removeEventListener('focus', onFocus)
    }
  }, [])

  useEffect(() => {
    if (jobs.length === 0) return
    Promise.all(
      jobs.slice(0, 5).map(j =>
        api.get('/evaluations', { params: { job_id: j.id } })
          .then(r => r.data.evaluations as Evaluation[])
          .catch(() => [] as Evaluation[]),
      ),
    ).then(results => {
      const all = results.flat().sort((a, b) =>
        (b.created_at || '').localeCompare(a.created_at || ''),
      )
      setAllEvals(all)
    })
  }, [jobs])

  useEffect(() => {
    if (jobs.length === 0) {
      setAllApplications([])
      return
    }
    Promise.all(
      jobs.slice(0, 8).map(job =>
        api.get(`/jobs/${job.id}/applications`)
          .then(r => r.data.applications as Application[])
          .catch(() => [] as Application[]),
      ),
    ).then(results => {
      const merged = results
        .flat()
        .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
      setAllApplications(merged)
    })
  }, [jobs])

  const activeJobs   = jobs.filter(j => j.is_active)
  const totalApps    = jobs.reduce((s, j) => s + (j.application_count || 0), 0)
  const shortlisted  = allEvals.filter(e => e.recruiter_action === 'shortlisted').length
  const doneEvals    = allEvals.filter(e => e.eval_status === 'done')
  const avgScore     = doneEvals.length
    ? Math.round(doneEvals.reduce((s, e) => s + (e.score ?? 0), 0) / doneEvals.length)
    : null
  const pendingReviewApps = allApplications.filter(app =>
    app.status === 'applied' || app.status === 'in_review' || !app.match_score,
  )
  const jobsNeedingAttention = activeJobs
    .map(job => ({
      ...job,
      pending_count: allApplications.filter(app =>
        app.job_id === job.id && (app.status === 'applied' || app.status === 'in_review'),
      ).length,
    }))
    .filter(job => job.pending_count > 0)
    .sort((a, b) => b.pending_count - a.pending_count)
    .slice(0, 5)
  const recentApplicants = allApplications.slice(0, 6)

  return (
    <RecruiterLayout>
      <div className="p-5 lg:p-6 max-w-[1400px] mx-auto space-y-5">

        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome, {user?.full_name?.split(' ')[0]} 👋
            </h1>
            <p className="text-gray-500 text-sm mt-0.5">
              {user?.recruiter?.company_name || 'Your hiring dashboard'}
            </p>
          </div>
          <button onClick={() => navigate('/dashboard/jobs')} className="btn-primary">
            <Plus className="w-4 h-4" /> Post a Job
          </button>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KpiCard
            label="Active Jobs"
            value={activeJobs.length}
            sub={`${jobs.length} total`}
            icon={<Briefcase className="w-4 h-4 text-white" />}
            gradient="bg-gradient-to-br from-brand-500 to-brand-700"
            loading={loading}
          />
          <KpiCard
            label="Total Applicants"
            value={totalApps}
            sub="across all jobs"
            icon={<Users className="w-4 h-4 text-white" />}
            gradient="bg-gradient-to-br from-purple-500 to-purple-700"
            loading={loading}
          />
          <KpiCard
            label="Avg Match Score"
            value={avgScore != null ? `${avgScore}%` : '—'}
            sub={`${doneEvals.length} evaluated`}
            icon={<TrendingUp className="w-4 h-4 text-white" />}
            gradient={
              avgScore == null ? 'bg-gradient-to-br from-gray-400 to-gray-500' :
              avgScore >= 70   ? 'bg-gradient-to-br from-yellow-400 to-orange-500' :
                                 'bg-gradient-to-br from-orange-400 to-red-500'
            }
            loading={loading}
          />
          <KpiCard
            label="Shortlisted"
            value={shortlisted}
            sub={allEvals.length > 0 ? `${Math.round((shortlisted / allEvals.length) * 100)}% rate` : '—'}
            icon={<CheckCircle2 className="w-4 h-4 text-white" />}
            gradient="bg-gradient-to-br from-green-500 to-emerald-600"
            loading={loading}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="card p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-semibold text-gray-800">Hiring Queue</p>
                <p className="text-xs text-gray-500 mt-0.5">Candidates waiting for recruiter attention</p>
              </div>
              <button
                onClick={() => navigate('/dashboard/candidates')}
                className="text-xs text-brand-600 hover:underline"
              >
                Open pipeline
              </button>
            </div>
            {pendingReviewApps.length === 0 ? (
              <div className="text-sm text-gray-500">No pending candidate reviews right now.</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-xl bg-amber-50 border border-amber-100 p-4">
                  <p className="text-xs text-amber-700 font-medium">Awaiting Review</p>
                  <p className="text-2xl font-bold text-amber-900 mt-1">{pendingReviewApps.length}</p>
                </div>
                <div className="rounded-xl bg-blue-50 border border-blue-100 p-4">
                  <p className="text-xs text-blue-700 font-medium">Recent Applicants</p>
                  <p className="text-2xl font-bold text-blue-900 mt-1">{recentApplicants.length}</p>
                </div>
                <div className="rounded-xl bg-purple-50 border border-purple-100 p-4">
                  <p className="text-xs text-purple-700 font-medium">Jobs Needing Review</p>
                  <p className="text-2xl font-bold text-purple-900 mt-1">{jobsNeedingAttention.length}</p>
                </div>
              </div>
            )}
          </div>

          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-semibold text-gray-800">Quick Actions</p>
              <Zap className="w-4 h-4 text-brand-500" />
            </div>
            <div className="space-y-2">
              {[
                { label: 'Review candidates', hint: 'Open shortlist and pending profiles', to: '/dashboard/candidates', icon: <Users className="w-4 h-4" /> },
                { label: 'Manage jobs', hint: 'Create or edit openings', to: '/dashboard/jobs', icon: <Briefcase className="w-4 h-4" /> },
                { label: 'Open messages', hint: 'Reply to candidate conversations', to: '/dashboard/messages', icon: <MessageSquare className="w-4 h-4" /> },
              ].map(action => (
                <button
                  key={action.label}
                  onClick={() => navigate(action.to)}
                  className="w-full flex items-center justify-between rounded-xl border border-gray-100 px-3 py-3 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center text-gray-700">
                      {action.icon}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{action.label}</p>
                      <p className="text-xs text-gray-500">{action.hint}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-gray-700">Evaluation Activity</p>
              <span className="text-xs text-gray-400">Last 7 days</span>
            </div>
            <EvalTrendChart evaluations={allEvals} loading={loading} />
          </div>
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-gray-700">Pipeline Breakdown</p>
              <span className="text-xs text-gray-400">{allEvals.length} total</span>
            </div>
            <PipelineDonut evaluations={allEvals} loading={loading} />
          </div>
        </div>

        {/* Jobs + Evaluations side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

          {/* Jobs */}
          <Section
            title="Your Jobs"
            action={() => navigate('/dashboard/jobs')}
            actionLabel="Manage all"
          >
            {loading ? (
              <div className="flex items-center justify-center py-6">
                <RefreshCw className="w-5 h-5 text-gray-400 animate-spin" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="text-center py-6">
                <Briefcase className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500 text-sm mb-3">No jobs posted yet</p>
                <button onClick={() => navigate('/dashboard/jobs')} className="btn-primary text-sm">
                  Post your first job
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {jobs.slice(0, 6).map(job => (
                  <div
                    key={job.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => navigate('/dashboard/candidates')}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-medium text-sm text-gray-900 truncate">{job.title}</p>
                        <span className={cn(
                          'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                          job.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500',
                        )}>
                          {job.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500">{job.location} · {timeAgo(job.created_at)}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold text-gray-900">{job.application_count || 0}</p>
                      <p className="text-[10px] text-gray-500">applicants</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* Recent evaluations */}
          <Section
            title="Recent AI Evaluations"
            action={() => navigate('/dashboard/candidates')}
            actionLabel="View all"
            defaultOpen={true}
          >
            {allEvals.length === 0 ? (
              <div className="text-center py-6 text-gray-400 text-sm">
                <Zap className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No evaluations yet
              </div>
            ) : (
              <div className="space-y-2">
                {allEvals.slice(0, 6).map(ev => {
                  const rec = recommendationBadge(ev.recommendation)
                  return (
                    <div
                      key={ev.id}
                      className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => navigate('/dashboard/candidates')}
                    >
                      <div className={cn(
                        'text-xs font-bold px-2 py-0.5 rounded-lg min-w-[44px] text-center',
                        scoreBg(ev.score),
                      )}>
                        {ev.score != null ? `${ev.score}%` : ev.eval_status === 'running' ? '…' : '—'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {ev.candidate?.full_name || `Candidate #${ev.candidate_id}`}
                        </p>
                        <p className="text-xs text-gray-500 truncate">{ev.job?.title}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={cn('badge text-[10px]', rec.cls)}>{rec.label}</span>
                        {ev.recruiter_action === 'shortlisted' && (
                          <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">SL</span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Section>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Section
            title="Recent Applicants"
            action={() => navigate('/dashboard/candidates')}
            actionLabel="Open candidates"
          >
            {recentApplicants.length === 0 ? (
              <div className="text-center py-6 text-gray-400 text-sm">
                <Users className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No applications received yet
              </div>
            ) : (
              <div className="space-y-2">
                {recentApplicants.map(app => (
                  <div
                    key={app.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {app.candidate?.full_name || `Candidate #${app.candidate_id}`}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {app.job?.title || 'Job'} · {timeAgo(app.created_at)}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs font-medium text-gray-700">{app.status.replace('_', ' ')}</p>
                      <p className="text-[10px] text-gray-500">{app.match_score != null ? `${app.match_score}% match` : 'Not evaluated'}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section
            title="Jobs Needing Attention"
            action={() => navigate('/dashboard/jobs')}
            actionLabel="Manage jobs"
          >
            {jobsNeedingAttention.length === 0 ? (
              <div className="text-center py-6 text-gray-400 text-sm">
                <Clock3 className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No active jobs are waiting on review
              </div>
            ) : (
              <div className="space-y-2">
                {jobsNeedingAttention.map(job => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{job.title}</p>
                      <p className="text-xs text-gray-500 truncate">{job.location || 'Location not set'}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold text-amber-700">{job.pending_count}</p>
                      <p className="text-[10px] text-gray-500">pending reviews</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>

      </div>
    </RecruiterLayout>
  )
}
