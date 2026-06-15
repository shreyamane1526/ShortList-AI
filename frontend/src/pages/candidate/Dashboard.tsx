import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2, Clock, AlertCircle, RefreshCw, Play,
  Briefcase, TrendingUp, Star, Zap, ArrowRight,
  Github, Code2, FileText,
} from 'lucide-react'
import CandidateLayout from '@/components/layout/CandidateLayout'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import { cn, lcTotal } from '@/lib/utils'
import type { EnrichmentStatus, Evaluation, Notification } from '@/types'
import toast from 'react-hot-toast'

import ProfileSummaryCard    from '@/components/dashboard/ProfileSummaryCard'
import ApplicationTrendChart from '@/components/dashboard/ApplicationTrendChart'
import SkillMatchChart       from '@/components/dashboard/SkillMatchChart'
import JobTrackerKanban      from '@/components/dashboard/JobTrackerKanban'
import AIInsightsPanel       from '@/components/dashboard/AIInsightsPanel'
import ActivityFeed          from '@/components/dashboard/ActivityFeed'

// ── Agent enrichment step ─────────────────────────────────────────────────────
const AGENT_LABELS: Record<string, string> = {
  github: 'GitHub', leetcode: 'LeetCode', resume: 'Resume', job_match: 'Job Match',
}

function AgentStep({ name, status }: { name: string; status: string }) {
  const icon =
    status === 'done'    ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> :
    status === 'running' ? <RefreshCw    className="w-3.5 h-3.5 text-brand-500 animate-spin" /> :
    status === 'error'   ? <AlertCircle  className="w-3.5 h-3.5 text-red-500" /> :
                           <Clock        className="w-3.5 h-3.5 text-gray-300" />
  return (
    <div className="flex items-center gap-2 py-1.5">
      {icon}
      <span className={cn('text-xs', status === 'done' ? 'text-gray-800 font-medium' : 'text-gray-500')}>
        {AGENT_LABELS[name] || name}
      </span>
      <span className={cn(
        'ml-auto text-[10px] px-1.5 py-0.5 rounded-full',
        status === 'done'    ? 'bg-green-100 text-green-700' :
        status === 'running' ? 'bg-blue-100 text-blue-700' :
        status === 'error'   ? 'bg-red-100 text-red-600' :
                               'bg-gray-100 text-gray-400',
      )}>
        {status}
      </span>
    </div>
  )
}

// ── Gradient stat card ────────────────────────────────────────────────────────
function StatCard({
  label, value, sub, icon, gradient,
}: {
  label: string; value: string | number; sub?: string
  icon: React.ReactNode; gradient: string
}) {
  return (
    <div className={cn('rounded-xl p-4 text-white', gradient)}>
      <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center mb-3">
        {icon}
      </div>
      <p className="text-xl font-bold leading-none">{value}</p>
      <p className="text-xs text-white/80 mt-1">{label}</p>
      {sub && <p className="text-[10px] text-white/60 mt-0.5">{sub}</p>}
    </div>
  )
}

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse bg-gray-100 rounded-xl', className)} />
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export default function CandidateDashboard() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const candidate = user?.candidate

  const [enrichStatus,  setEnrichStatus]  = useState<EnrichmentStatus | null>(null)
  const [evaluations,   setEvaluations]   = useState<Evaluation[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loadingInit,   setLoadingInit]   = useState(true)

  const fetchEnrichStatus = useCallback(async () => {
    try {
      const res = await api.get('/me/profile/enrichment-status')
      setEnrichStatus(res.data)
      return res.data.enrichment_status as string
    } catch { return 'error' }
  }, [])

  const fetchEvaluations = useCallback(async () => {
    try {
      const res = await api.get('/candidate/evaluations')
      setEvaluations(res.data.evaluations)
    } catch { /* ignore */ }
  }, [])

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await api.get('/me/notifications')
      setNotifications(res.data.notifications)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    Promise.all([fetchEnrichStatus(), fetchEvaluations(), fetchNotifications()])
      .finally(() => setLoadingInit(false))
  }, [fetchEnrichStatus, fetchEvaluations, fetchNotifications])

  // Poll enrichment
  useEffect(() => {
    if (!enrichStatus) return
    const s = enrichStatus.enrichment_status
    if (s !== 'pending' && s !== 'running') return
    const id = setInterval(async () => {
      const next = await fetchEnrichStatus()
      if (next === 'done' || next === 'partial' || next === 'error') {
        clearInterval(id)
        refreshUser()
        if (next !== 'error') toast.success('Profile analysis complete!')
        else toast.error('Analysis finished with errors')
      }
    }, 2500)
    return () => clearInterval(id)
  }, [enrichStatus?.enrichment_status, fetchEnrichStatus, refreshUser])

  // Poll pending evaluations
  useEffect(() => {
    const pending = evaluations.filter(e => e.eval_status === 'pending' || e.eval_status === 'running')
    if (!pending.length) return
    const id = setInterval(fetchEvaluations, 3000)
    return () => clearInterval(id)
  }, [evaluations, fetchEvaluations])

  const isEnriching = enrichStatus?.enrichment_status === 'pending' || enrichStatus?.enrichment_status === 'running'
  const enrichDone  = enrichStatus?.enrichment_status === 'done'    || enrichStatus?.enrichment_status === 'partial'
  const enrichNone  = !enrichStatus?.enrichment_status || enrichStatus.enrichment_status === 'none'
  const agentStatuses = enrichStatus?.agent_statuses || {}

  const doneEvals   = evaluations.filter(e => e.eval_status === 'done')
  const shortlisted = evaluations.filter(e => e.recruiter_action === 'shortlisted').length
  const avgScore    = doneEvals.length
    ? Math.round(doneEvals.reduce((s, e) => s + (e.score ?? 0), 0) / doneEvals.length)
    : null

  const allSkills = [...new Set([...(candidate?.skills || []), ...(enrichStatus?.resume_skills || [])])]

  const profileFields = [
    !!candidate?.headline, !!candidate?.location, !!candidate?.summary,
    !!candidate?.github_username, !!candidate?.leetcode_username,
    !!candidate?.resume_url, (candidate?.skills?.length ?? 0) > 0,
    (candidate?.projects?.length ?? 0) > 0,
  ]
  const profileStrength = Math.round((profileFields.filter(Boolean).length / profileFields.length) * 100)

  async function triggerEnrichment() {
    try {
      const form = new FormData()
      if (candidate?.github_username)   form.append('github_username',   candidate.github_username)
      if (candidate?.leetcode_username) form.append('leetcode_username', candidate.leetcode_username)
      await api.post('/me/profile/enrich', form, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success('AI analysis started!')
      fetchEnrichStatus()
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to start analysis')
    }
  }

  const hasAnyData = candidate?.github_username || candidate?.leetcode_username || candidate?.resume_url
  const neverSetup = !hasAnyData && enrichStatus?.enrichment_status === 'none'

  // ── Empty state ───────────────────────────────────────────────────────────
  if (!loadingInit && neverSetup) {
    return (
      <CandidateLayout>
        <div className="flex items-center justify-center h-full p-8">
          <div className="text-center max-w-sm">
            <div className="w-16 h-16 bg-brand-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-8 h-8 text-brand-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Complete your profile</h2>
            <p className="text-gray-500 text-sm mb-6">
              Add your GitHub, LeetCode, and resume so AI agents can analyze your skills.
            </p>
            <button onClick={() => navigate('/candidate/onboarding')} className="btn-primary">
              Set Up Profile
            </button>
          </div>
        </div>
      </CandidateLayout>
    )
  }

  // ── Main ──────────────────────────────────────────────────────────────────
  return (
    <CandidateLayout>
      {/* Outer scroll container — fills the layout's <main> */}
      <div className="min-h-full bg-gray-50 p-5 lg:p-6">
        <div className="max-w-screen-xl mx-auto space-y-5">

          {/* ── Header ─────────────────────────────────────────────────── */}
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Welcome back, {user?.full_name?.split(' ')[0]} 👋
              </h1>
              <p className="text-gray-500 text-sm mt-0.5">Your AI-powered career hub</p>
            </div>
            <button onClick={() => navigate('/candidate/applications')} className="btn-secondary text-sm">
              All Applications <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* ── Enrichment banners ─────────────────────────────────────── */}
          {enrichNone && (candidate?.github_username || candidate?.leetcode_username) && (
            <div className="card p-4 border-brand-200 bg-brand-50 flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="font-semibold text-brand-900 text-sm">Profile not analyzed yet</p>
                <p className="text-xs text-brand-700 mt-0.5">
                  Run AI agents to analyze your GitHub{candidate?.leetcode_username ? ', LeetCode,' : ''} and resume.
                </p>
              </div>
              <button onClick={triggerEnrichment} className="btn-primary shrink-0 text-sm">
                <Play className="w-3.5 h-3.5" /> Run Analysis
              </button>
            </div>
          )}

          {isEnriching && (
            <div className="card p-4 border-brand-200 bg-brand-50">
              <div className="flex items-center gap-3 mb-3">
                <RefreshCw className="w-4 h-4 text-brand-600 animate-spin" />
                <div>
                  <p className="font-semibold text-brand-900 text-sm">AI agents are analyzing your profile…</p>
                  <p className="text-xs text-brand-700">This takes 30–60 seconds. Results appear automatically.</p>
                </div>
              </div>
              <div className="divide-y divide-brand-100">
                {Object.entries(agentStatuses).map(([name, status]) => (
                  <AgentStep key={name} name={name} status={status} />
                ))}
                {!Object.keys(agentStatuses).length && <AgentStep name="github" status="running" />}
              </div>
            </div>
          )}

          {/* ── 4 stat cards ───────────────────────────────────────────── */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {loadingInit ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
            ) : (
              <>
                <StatCard
                  label="Applications"
                  value={evaluations.length}
                  sub={`${doneEvals.length} evaluated`}
                  icon={<Briefcase className="w-4 h-4 text-white" />}
                  gradient="bg-gradient-to-br from-brand-500 to-brand-700"
                />
                <StatCard
                  label="Shortlisted"
                  value={shortlisted}
                  sub={evaluations.length ? `${Math.round((shortlisted / evaluations.length) * 100)}% rate` : '—'}
                  icon={<CheckCircle2 className="w-4 h-4 text-white" />}
                  gradient="bg-gradient-to-br from-green-500 to-emerald-600"
                />
                <StatCard
                  label="Avg Score"
                  value={avgScore != null ? `${avgScore}%` : '—'}
                  sub={doneEvals.length ? `${doneEvals.length} evals` : 'No evals yet'}
                  icon={<Star className="w-4 h-4 text-white" />}
                  gradient={
                    avgScore == null      ? 'bg-gradient-to-br from-gray-400 to-gray-500' :
                    avgScore >= 75        ? 'bg-gradient-to-br from-yellow-400 to-orange-500' :
                    avgScore >= 50        ? 'bg-gradient-to-br from-yellow-500 to-yellow-600' :
                                            'bg-gradient-to-br from-red-400 to-red-600'
                  }
                />
                <StatCard
                  label="Profile Strength"
                  value={`${profileStrength}%`}
                  sub={profileStrength < 100 ? 'Tap to complete' : 'Complete!'}
                  icon={<Zap className="w-4 h-4 text-white" />}
                  gradient={
                    profileStrength >= 80 ? 'bg-gradient-to-br from-purple-500 to-purple-700' :
                    profileStrength >= 50 ? 'bg-gradient-to-br from-indigo-400 to-indigo-600' :
                                            'bg-gradient-to-br from-slate-400 to-slate-600'
                  }
                />
              </>
            )}
          </div>

          {/* ── Main 2-column layout ────────────────────────────────────── */}
          {/*   Left sidebar (320px) | Right main area (flex-1)            */}
          <div className="flex gap-5 items-start">

            {/* ── LEFT SIDEBAR ─────────────────────────────────────────── */}
            <div className="w-72 xl:w-80 shrink-0 space-y-4">

              {/* Profile card */}
              <div className="card p-5">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Profile</p>
                {candidate
                  ? <ProfileSummaryCard candidate={candidate} enrichStatus={enrichStatus} />
                  : <Skeleton className="h-52" />}
              </div>

              {/* GitHub / LeetCode quick stats */}
              {enrichDone && (
                <div className="card p-4 space-y-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Activity</p>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
                      <Github className="w-4 h-4 text-gray-700" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900">
                        {enrichStatus?.github_repos ?? '—'} repos
                      </p>
                      <p className="text-xs text-gray-500">{enrichStatus?.github_stars ?? 0} ⭐</p>
                    </div>
                    {enrichStatus?.github_top_languages?.length ? (
                      <div className="flex gap-1">
                        {enrichStatus.github_top_languages.slice(0, 2).map(l => (
                          <span key={l} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                            {l}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  {enrichStatus?.lc_easy != null && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-orange-50 flex items-center justify-center shrink-0">
                        <Code2 className="w-4 h-4 text-orange-500" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-gray-900">
                          {lcTotal(enrichStatus.lc_easy, enrichStatus.lc_medium, enrichStatus.lc_hard)} solved
                        </p>
                        <p className="text-xs text-gray-500">
                          {enrichStatus.lc_easy}E · {enrichStatus.lc_medium}M · {enrichStatus.lc_hard}H
                        </p>
                      </div>
                    </div>
                  )}
                  {enrichStatus?.resume_skills?.length ? (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center shrink-0">
                        <FileText className="w-4 h-4 text-purple-500" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {enrichStatus.resume_skills.length} skills
                        </p>
                        <p className="text-xs text-gray-500">from resume</p>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}

              {/* AI Insights */}
              <div className="card p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-3.5 h-3.5 text-brand-500" />
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">AI Insights</p>
                </div>
                <AIInsightsPanel evaluations={evaluations} loading={loadingInit} />
              </div>

            </div>

            {/* ── RIGHT MAIN AREA ──────────────────────────────────────── */}
            <div className="flex-1 min-w-0 space-y-4">

              {/* Charts row — side by side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-5">
                  <ApplicationTrendChart evaluations={evaluations} loading={loadingInit} />
                </div>
                <div className="card p-5">
                  <SkillMatchChart
                    evaluations={evaluations}
                    candidateSkills={allSkills}
                    loading={loadingInit}
                  />
                </div>
              </div>

              {/* Activity feed + Job tracker side by side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                {/* Activity feed */}
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm font-semibold text-gray-700">Activity Feed</p>
                    <button
                      onClick={() => navigate('/candidate/applications')}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      View all
                    </button>
                  </div>
                  <ActivityFeed
                    evaluations={evaluations}
                    notifications={notifications}
                    loading={loadingInit}
                  />
                </div>

                {/* Skills cloud */}
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm font-semibold text-gray-700">Your Skills</p>
                    <span className="text-xs text-gray-400">{allSkills.length} total</span>
                  </div>
                  {loadingInit ? (
                    <Skeleton className="h-32" />
                  ) : allSkills.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">
                      No skills yet — run profile analysis
                    </p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {allSkills.slice(0, 30).map(s => (
                        <span
                          key={s}
                          className="text-xs bg-brand-50 text-brand-700 border border-brand-200 px-2.5 py-0.5 rounded-full"
                        >
                          {s}
                        </span>
                      ))}
                      {allSkills.length > 30 && (
                        <span className="text-xs text-gray-400 px-2 py-0.5">
                          +{allSkills.length - 30} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Job tracker — full width inside main area */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm font-semibold text-gray-700">Job Tracker</p>
                  <button
                    onClick={() => navigate('/candidate/applications')}
                    className="text-xs text-brand-600 hover:underline"
                  >
                    Manage
                  </button>
                </div>
                <JobTrackerKanban evaluations={evaluations} />
              </div>

            </div>
          </div>

        </div>
      </div>
    </CandidateLayout>
  )
}
