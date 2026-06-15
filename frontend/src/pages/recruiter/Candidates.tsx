import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Search, RefreshCw, Github, Code2,
  CheckCircle2, XCircle, MessageSquare, Zap, BookOpen,
  SlidersHorizontal, Download, Trophy, ChevronDown, ChevronUp,
} from 'lucide-react'
import RecruiterLayout from '@/components/layout/RecruiterLayout'
import Modal from '@/components/ui/Modal'
import ScoreRing from '@/components/ui/ScoreRing'
import WhyNotSelected from '@/components/feedback/WhyNotSelected'
import SkillMatchVisualization from '@/components/feedback/SkillMatchVisualization'
import LearningPath from '@/components/feedback/LearningPath'
import ConfidenceScoreCard from '@/components/feedback/ConfidenceScoreCard'
import BadgeRow from '@/components/feedback/BadgeRow'
import { InclusionBadge } from '@/components/inclusion/InclusionBadge'
import { InclusionToggle } from '@/components/inclusion/InclusionToggle'
import api from '@/lib/api'
import { cn, initials, lcTotal, scoreBg, recommendationBadge, timeAgo } from '@/lib/utils'
import type { DashboardCandidate, Job, Evaluation, CulturalDNA } from '@/types'
import type { RichFeedbackReport } from '@/types/feedback'
import toast from 'react-hot-toast'
import ReactMarkdown from 'react-markdown'
import CulturalDNACard from '@/components/feedback/CulturalDNACard'
// ── CSV export helper ─────────────────────────────────────────────────────────
function exportCSV(candidates: DashboardCandidate[]) {
  const headers = ['Name', 'Email', 'Headline', 'Skills', 'GitHub Repos', 'LeetCode', 'Score', 'Status', 'Job']
  const rows = candidates.map(c => [
    c.full_name,
    c.email ?? '',
    c.headline ?? '',
    [...c.skills, ...c.resume_skills].join('; '),
    c.github_repos ?? '',
    lcTotal(c.lc_easy, c.lc_medium, c.lc_hard),
    c.latest_evaluation?.score ?? '',
    c.latest_evaluation?.recruiter_action ?? '',
    c.latest_evaluation?.job_title ?? '',
  ])
  const csv = [headers, ...rows]
    .map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = `candidates-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Bulk action bar ───────────────────────────────────────────────────────────
function BulkBar({
  count, onShortlist, onReject, onExport, onClear, loading,
}: {
  count: number
  onShortlist: () => void
  onReject: () => void
  onExport: () => void
  onClear: () => void
  loading: boolean
}) {
  if (count === 0) return null
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-gray-900 text-white px-5 py-3 rounded-2xl shadow-2xl border border-gray-700">
      <span className="w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center text-xs font-bold shrink-0">
        {count}
      </span>
      <span className="text-sm font-medium mr-1">{count} selected</span>
      <div className="w-px h-5 bg-gray-600" />
      <button onClick={onShortlist} disabled={loading}
        className="flex items-center gap-1.5 text-sm font-medium text-green-400 hover:text-green-300 disabled:opacity-50 transition-colors"
        title="Shortlist (S)">
        {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
        Shortlist
      </button>
      <button onClick={onReject} disabled={loading}
        className="flex items-center gap-1.5 text-sm font-medium text-red-400 hover:text-red-300 disabled:opacity-50 transition-colors"
        title="Reject (R)">
        <XCircle className="w-4 h-4" /> Reject
      </button>
      <button onClick={onExport}
        className="flex items-center gap-1.5 text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
        title="Export CSV">
        <Download className="w-4 h-4" /> Export
      </button>
      <div className="w-px h-5 bg-gray-600" />
      <button onClick={onClear} className="text-gray-400 hover:text-white transition-colors text-xs">
        ✕ Clear
      </button>
    </div>
  )
}

// ── Leaderboard widget ────────────────────────────────────────────────────────
function Leaderboard({
  candidates, onOpen,
}: {
  candidates: DashboardCandidate[]
  onOpen: (c: DashboardCandidate) => void
}) {
  const top = candidates
    .filter(c => c.latest_evaluation?.score != null)
    .sort((a, b) => (b.latest_evaluation!.score! - a.latest_evaluation!.score!))
    .slice(0, 5)
  if (!top.length) return null
  const medals = ['🥇', '🥈', '🥉']
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="w-4 h-4 text-yellow-500" />
        <span className="text-sm font-semibold text-gray-700">Top Candidates</span>
      </div>
      <div className="space-y-2">
        {top.map((c, i) => (
          <button key={c.id} onClick={() => onOpen(c)}
            className="w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-gray-50 transition-colors text-left">
            <span className="text-base w-5 shrink-0">{medals[i] ?? `${i + 1}.`}</span>
            <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold shrink-0">
              {initials(c.full_name)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-900 truncate">{c.full_name}</p>
              <p className="text-[10px] text-gray-500 truncate">{c.latest_evaluation?.job_title}</p>
            </div>
            <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full shrink-0', scoreBg(c.latest_evaluation?.score))}>
              {c.latest_evaluation?.score}%
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
function normalizeCulturalDNA(
  culturalDNA: Evaluation['cultural_dna'],
  candidateName: string,
): CulturalDNA | null {
  if (!culturalDNA || !Array.isArray(culturalDNA.dimensions) || culturalDNA.dimensions.length === 0) {
    return null
  }

  return {
    overall_match_pct: culturalDNA.overall_match_pct ?? 0,
    signal_type: culturalDNA.signal_type ?? 'Behavioral signals only',
    candidate_name: culturalDNA.candidate_name || candidateName,
    company_name: culturalDNA.company_name || 'Company',
    dimensions: culturalDNA.dimensions,
  }
}

export default function RecruiterCandidates() {
  const [candidates, setCandidates] = useState<DashboardCandidate[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [skillFilter, setSkillFilter] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [actionFilter, setActionFilter] = useState('')
  const [githubFilter, setGithubFilter] = useState('')
  const [sortBy, setSortBy] = useState<'score' | 'name' | 'date'>('score')
  const [showFilters, setShowFilters] = useState(false)

  // Bulk selection
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)

  // Modals
  const [detailModal, setDetailModal] = useState<{
    candidate: DashboardCandidate
    evaluations: Evaluation[]
    richFeedback: Record<number, RichFeedbackReport>
  } | null>(null)
  const [evaluating, setEvaluating] = useState<string | null>(null)
  const [actioning, setActioning] = useState<number | null>(null)
  const [msgModal, setMsgModal] = useState<{ userId: number; name: string } | null>(null)
  const [msgBody, setMsgBody] = useState('')
  const [sendingMsg, setSendingMsg] = useState(false)
  const fetchInFlightRef = useRef(false)
  const latestReqIdRef = useRef(0)

  // ── Data fetching ───────────────────────────────────────────────────────────
  useEffect(() => {
    fetchCandidates()
    api.get('/jobs').then(r => setJobs(r.data.jobs)).catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchCandidates = useCallback(async (opts?: { force?: boolean; silent?: boolean }) => {
    if (fetchInFlightRef.current && !opts?.force) return
    fetchInFlightRef.current = true
    const reqId = ++latestReqIdRef.current
    if (!opts?.silent) setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = {}
      if (skillFilter) params.skill = skillFilter
      if (minScore > 0) params.min_score = minScore
      if (actionFilter) params.recruiter_action = actionFilter
      if (selectedJobId) params.job_id = selectedJobId
      // Use recruiter-scoped endpoint which returns applications for recruiter's jobs
      const res = await api.get('/recruiter/candidates', { params })
      if (reqId !== latestReqIdRef.current) return
      // Backend returns list of applications — adapt to DashboardCandidate shape
      const apps = res.data.candidates || []
      const transformed = apps.map((a: any) => {
        const cand = a.candidate || {}
        const ev = a.latest_evaluation || null
        const evaluation = ev ? {
          id: ev.id ?? a.id,
          job_id: ev.job_id ?? a.job_id,
          job_title: ev.job?.title ?? ev.job_title ?? a.job?.title ?? null,
          job_company: ev.job?.company ?? a.job?.company ?? '',
          score: ev.score ?? a.match_score ?? null,
          recommendation: ev.recommendation ?? 'PENDING',
          recruiter_action: ev.recruiter_action ?? a.status ?? 'pending',
          strengths: ev.strengths ?? [],
          gaps: ev.gaps ?? [],
          why_fit: ev.why_fit ?? null,
          evaluated_at: ev.evaluated_at ?? null,
          eval_status: ev.eval_status ?? null,
          eval_error: ev.eval_error ?? null,
        } : null
        return {
          id: cand.id ?? a.candidate_id ?? a.id,
          user_id: cand.user_id ?? null,
          full_name: cand.full_name ?? '',
          email: cand.email ?? null,
          headline: cand.headline ?? null,
          location: cand.location ?? null,
          years_experience: cand.years_experience ?? null,
          skills: cand.skills || [],
          resume_skills: cand.resume_skills || [],
          github_username: cand.github_username ?? null,
          github_repos: cand.github_repos ?? null,
          github_stars: cand.github_stars ?? null,
          lc_easy: cand.lc_easy ?? null,
          lc_medium: cand.lc_medium ?? null,
          lc_hard: cand.lc_hard ?? null,
          top_skill: cand.top_skill ?? ((cand.skills || cand.resume_skills || ['N/A'])[0]),
          created_at: cand.created_at || a.created_at,
          latest_evaluation: evaluation,
        }
      })
      setCandidates(transformed)
      setSelected(new Set()) // clear selection on refresh
    } catch (e: any) {
      if (reqId !== latestReqIdRef.current) return
      setError(e?.response?.data?.error || 'Failed to load candidates')
    } finally {
      if (reqId === latestReqIdRef.current) {
        fetchInFlightRef.current = false
        if (!opts?.silent) setLoading(false)
      }
    }
  }, [skillFilter, minScore, actionFilter, selectedJobId])

  useEffect(() => {
    const t = window.setTimeout(() => { fetchCandidates() }, 250)
    return () => window.clearTimeout(t)
  }, [fetchCandidates])

  useEffect(() => {
    const hasPending = candidates.some(c => {
      const ev = c.latest_evaluation as (Evaluation & { eval_status?: string }) | null
      return ev && (ev.eval_status === 'pending' || ev.eval_status === 'running')
    })
    if (!hasPending) return
    const id = window.setInterval(() => { fetchCandidates({ silent: true }) }, 30000)
    return () => window.clearInterval(id)
  }, [candidates, fetchCandidates])

  useEffect(() => {
    const id = window.setInterval(() => { fetchCandidates({ silent: true }) }, 45000)
    return () => window.clearInterval(id)
  }, [fetchCandidates])

  // ── Keyboard shortcuts ──────────────────────────────────────────────────────
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'Escape') { setSelected(new Set()); return }
      if (!selected.size) return
      if (e.key === 's') { e.preventDefault(); handleBulkAction('shortlisted') }
      if (e.key === 'r') { e.preventDefault(); handleBulkAction('rejected') }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected])

  // ── Actions ─────────────────────────────────────────────────────────────────
  async function openDetail(c: DashboardCandidate) {
    try {
      const res = await api.get(`/candidates/${c.id}/full`)
      const evs: Evaluation[] = res.data.evaluations
      const richFeedback: Record<number, RichFeedbackReport> = {}
      for (const ev of evs) {
        if (ev.feedback_report) {
          const raw = ev.feedback_report as unknown as Record<string, unknown>
          richFeedback[ev.id] = raw.why_not_selected ? (raw as unknown as RichFeedbackReport) : {
            why_not_selected: { reasons: [], tone: 'constructive', improvement_hints: [] },
            improvement_plan: { short_term: [], long_term: [] },
            learning_path: [],
            skill_match_visualization: { required_skills: [], matched: [], missing: [], partial: [] },
            confidence_score: { score: ev.score ?? 50, level: 'Medium' as const, factors: [] },
            badges: [],
            candidate_report_markdown: (raw.candidate_report as string) || '',
            recruiter_summary: (raw.recruiter_summary as string) || '',
          }
        }
      }
      setDetailModal({ candidate: res.data.candidate, evaluations: evs, richFeedback })
    } catch { toast.error('Failed to load candidate details') }
  }

  async function triggerEvaluation(candidateId: number, jobId: number) {
    const key = `${candidateId}-${jobId}`
    setEvaluating(key)
    try {
      await api.post('/evaluate', { candidate_id: candidateId, job_id: jobId })
      setCandidates(prev => prev.map(c => c.id === candidateId ? {
        ...c,
        latest_evaluation: c.latest_evaluation ? {
          ...c.latest_evaluation,
          job_id: jobId,
          eval_status: 'pending',
          recommendation: 'PENDING',
          score: null,
          eval_error: null,
        } as any : {
          id: -1,
          candidate_id: c.id,
          job_id: jobId,
          score: null,
          recommendation: 'PENDING',
          strengths: [],
          gaps: [],
          why_fit: null,
          eval_status: 'pending',
          eval_error: null,
          recruiter_action: 'pending',
          action_taken_at: null,
          evaluated_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        } as any,
      } : c))
      toast.success('AI evaluation started!')
      fetchCandidates({ silent: true, force: true })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      toast.error(msg || 'Failed to start evaluation')
    } finally { setEvaluating(null) }
  }

  async function takeAction(evalId: number, action: 'shortlisted' | 'rejected' | 'pending') {
    setActioning(evalId)
    try {
      await api.post(`/evaluations/${evalId}/action`, { action })
      setCandidates(prev => prev.map(c => {
        const ev = c.latest_evaluation as any
        if (!ev || ev.id !== evalId) return c
        return { ...c, latest_evaluation: { ...ev, recruiter_action: action } }
      }))
      toast.success(
        action === 'shortlisted' ? 'Candidate shortlisted!' :
        action === 'rejected'    ? 'Candidate rejected' : 'Action reset',
      )
      fetchCandidates({ silent: true, force: true })
      if (detailModal) {
        const res = await api.get(`/candidates/${detailModal.candidate.id}/full`)
        setDetailModal(d => d ? { ...d, evaluations: res.data.evaluations } : null)
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      toast.error(msg || 'Failed to update')
    } finally { setActioning(null) }
  }

  async function handleBulkAction(action: 'shortlisted' | 'rejected') {
    if (!selected.size) return
    setBulkLoading(true)
    const targets = filtered.filter(c => selected.has(c.id) && c.latest_evaluation)
    let ok = 0
    for (const c of targets) {
      try {
        await api.post(`/evaluations/${c.latest_evaluation!.id}/action`, { action })
        ok++
      } catch { /* skip */ }
    }
    toast.success(`${ok} candidate${ok !== 1 ? 's' : ''} ${action}`)
    setSelected(new Set())
    setBulkLoading(false)
    fetchCandidates()
  }

  async function sendMessage() {
    if (!msgModal || !msgBody.trim()) return
    setSendingMsg(true)
    try {
      await api.post('/messages', {
        recipient_id: msgModal.userId,
        subject: 'Message from Recruiter',
        body: msgBody.trim(),
      })
      toast.success('Message sent!')
      setMsgModal(null)
      setMsgBody('')
    } catch { toast.error('Failed to send') } finally { setSendingMsg(false) }
  }

  // ── Selection helpers ───────────────────────────────────────────────────────
  function toggleSelect(id: number) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    if (selected.size === filtered.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filtered.map(c => c.id)))
    }
  }

  // ── Filtering / sorting ─────────────────────────────────────────────────────
  function githubActivity(c: DashboardCandidate): 'low' | 'medium' | 'high' {
    const r = c.github_repos ?? 0
    return r >= 20 ? 'high' : r >= 5 ? 'medium' : 'low'
  }

  const filtered = useMemo(() => candidates
    .filter(c => {
      if (search) {
        const q = search.toLowerCase()
        if (!c.full_name.toLowerCase().includes(q) &&
            !c.email?.toLowerCase().includes(q) &&
            !c.skills.some(s => s.toLowerCase().includes(q)) &&
            !c.resume_skills.some(s => s.toLowerCase().includes(q))) return false
      }
      if (githubFilter && githubActivity(c) !== githubFilter) return false
      return true
    })
    .sort((a, b) => {
      if (sortBy === 'name') return a.full_name.localeCompare(b.full_name)
      if (sortBy === 'date') return (b.created_at || '').localeCompare(a.created_at || '')
      return (b.latest_evaluation?.score ?? -1) - (a.latest_evaluation?.score ?? -1)
    }), [candidates, search, githubFilter, sortBy])

  const allSelected = filtered.length > 0 && selected.size === filtered.length
  const someSelected = selected.size > 0 && selected.size < filtered.length

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <RecruiterLayout>
      <div className="p-5 lg:p-6 max-w-screen-xl mx-auto space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Candidates</h1>
            <p className="text-gray-500 text-sm mt-0.5">{filtered.length} candidates</p>
          </div>
          <div className="flex items-center gap-2">
            <InclusionToggle
              jobId={selectedJobId || undefined}
              variant="minimal"
            />
            <button onClick={() => exportCSV(filtered)} className="btn-secondary text-sm">
              <Download className="w-4 h-4" /> Export CSV
            </button>
            <button onClick={fetchCandidates} className="btn-secondary">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Main layout: sidebar leaderboard + table */}
        <div className="flex gap-5 items-start">

          {/* Left: leaderboard (hidden on small screens) */}
          <div className="hidden xl:block w-56 shrink-0">
            <Leaderboard candidates={candidates} onOpen={openDetail} />
          </div>

          {/* Right: filters + table */}
          <div className="flex-1 min-w-0 space-y-4">

            {/* Filter bar */}
            <div className="space-y-3">
              <div className="flex gap-2 flex-wrap">
                <div className="relative flex-1 min-w-44">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input className="input pl-9" placeholder="Search name, skill, email…"
                    value={search} onChange={e => setSearch(e.target.value)} />
                </div>
                <select className="input w-48" value={selectedJobId} onChange={e => setSelectedJobId(e.target.value ? Number(e.target.value) : '')}>
                  <option value="">All jobs</option>
                  {jobs.map(j => <option key={j.id} value={j.id}>{j.title} ({j.application_count || 0})</option>)}
                </select>
                <select className="input w-36" value={actionFilter} onChange={e => setActionFilter(e.target.value)}>
                  <option value="">All statuses</option>
                  <option value="pending">Pending</option>
                  <option value="shortlisted">Shortlisted</option>
                  <option value="rejected">Rejected</option>
                </select>
                <select className="input w-32" value={sortBy} onChange={e => setSortBy(e.target.value as 'score' | 'name' | 'date')}>
                  <option value="score">Score ↓</option>
                  <option value="name">Name A–Z</option>
                  <option value="date">Newest</option>
                </select>
                <button
                  onClick={() => setShowFilters(f => !f)}
                  className={cn('btn-secondary', showFilters && 'bg-brand-50 border-brand-300 text-brand-700')}
                >
                  <SlidersHorizontal className="w-4 h-4" /> Filters
                </button>
              </div>

              {showFilters && (
                <div className="card p-4 grid sm:grid-cols-3 gap-4">
                  <div>
                    <label className="label">Skill filter</label>
                    <input className="input" placeholder="e.g. python"
                      value={skillFilter} onChange={e => setSkillFilter(e.target.value)} />
                  </div>
                  <div>
                    <label className="label">Job</label>
                    <select className="input" value={selectedJobId} onChange={e => setSelectedJobId(e.target.value ? Number(e.target.value) : '')}>
                      <option value="">All jobs</option>
                      {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Min score: {minScore > 0 ? `${minScore}%` : 'Any'}</label>
                    <input type="range" min={0} max={100} step={5} value={minScore}
                      onChange={e => setMinScore(Number(e.target.value))}
                      className="w-full accent-brand-600 mt-2" />
                  </div>
                  <div>
                    <label className="label">GitHub activity</label>
                    <select className="input" value={githubFilter} onChange={e => setGithubFilter(e.target.value)}>
                      <option value="">Any</option>
                      <option value="high">High (20+ repos)</option>
                      <option value="medium">Medium (5–19)</option>
                      <option value="low">Low (&lt;5)</option>
                    </select>
                  </div>
                  {/* Preset filters */}
                  <div className="sm:col-span-3">
                    <label className="label">Quick presets</label>
                    <div className="flex gap-2 flex-wrap">
                      {[
                        { label: '🔥 High Potential', action: () => { setMinScore(75); setActionFilter('pending') } },
                        { label: '⏳ Needs Review',   action: () => { setMinScore(50); setActionFilter('pending') } },
                        { label: '✅ Shortlisted',    action: () => { setActionFilter('shortlisted'); setMinScore(0) } },
                        { label: '🔄 Reset',          action: () => { setMinScore(0); setActionFilter(''); setSkillFilter(''); setGithubFilter('') } },
                      ].map(p => (
                        <button key={p.label} onClick={p.action}
                          className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 text-gray-700 transition-colors">
                          {p.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Evaluate panel */}
            {jobs.length > 0 && (
              <div className="card p-3 bg-brand-50 border-brand-200 flex items-center gap-3 flex-wrap">
                <Zap className="w-4 h-4 text-brand-600 shrink-0" />
                <span className="text-sm font-medium text-brand-900">Evaluate against:</span>
                <select className="input w-48 text-sm" value={selectedJobId}
                  onChange={e => setSelectedJobId(e.target.value ? Number(e.target.value) : '')}>
                  <option value="">Select job…</option>
                  {jobs.filter(j => j.is_active).map(j => (
                    <option key={j.id} value={j.id}>{j.title}</option>
                  ))}
                </select>
                <span className="text-xs text-brand-700">Then click ⚡ on a row</span>
              </div>
            )}

            {/* Keyboard shortcut hint */}
            {selected.size > 0 && (
              <p className="text-xs text-gray-400 text-center">
                Press <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-mono">S</kbd> to shortlist ·{' '}
                <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-mono">R</kbd> to reject ·{' '}
                <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-mono">Esc</kbd> to clear
              </p>
            )}

            {/* Table */}
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
              </div>
            ) : error ? (
              <div className="text-center py-10 text-red-500 text-sm">{error}</div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-16 text-gray-400">No candidates found</div>
            ) : (
              <div className="card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      <th className="px-4 py-3 w-8">
                        <input type="checkbox"
                          checked={allSelected}
                          ref={el => { if (el) el.indeterminate = someSelected }}
                          onChange={toggleSelectAll}
                          className="rounded accent-brand-600 cursor-pointer" />
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Candidate</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Skills</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">GitHub</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">LC</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Score</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filtered.map(c => {
                      const ev  = c.latest_evaluation
                      const rec = ev ? recommendationBadge(ev.recommendation) : null
                      const isSelected = selected.has(c.id)
                      return (
                        <tr key={c.id}
                          className={cn('transition-colors', isSelected ? 'bg-brand-50' : 'hover:bg-gray-50')}>
                          <td className="px-4 py-3">
                            <input type="checkbox" checked={isSelected}
                              onChange={() => toggleSelect(c.id)}
                              className="rounded accent-brand-600 cursor-pointer" />
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold shrink-0">
                                {initials(c.full_name)}
                              </div>
                              <div>
                                <p className="font-medium text-gray-900">{c.full_name}</p>
                                <p className="text-xs text-gray-500">{c.headline || c.email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 hidden md:table-cell">
                            <div className="flex flex-wrap gap-1 max-w-[160px]">
                              {[...c.skills, ...c.resume_skills].slice(0, 3).map(s => (
                                <span key={s} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{s}</span>
                              ))}
                              {([...c.skills, ...c.resume_skills].length > 3) && (
                                <span className="text-xs text-gray-400">+{[...c.skills, ...c.resume_skills].length - 3}</span>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3 hidden lg:table-cell">
                            {c.github_username
                              ? <div className="flex items-center gap-1 text-xs text-gray-600"><Github className="w-3 h-3" />{c.github_repos ?? 0}</div>
                              : <span className="text-xs text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-3 hidden lg:table-cell">
                            {c.lc_easy != null
                              ? <div className="flex items-center gap-1 text-xs text-gray-600"><Code2 className="w-3 h-3 text-orange-400" />{lcTotal(c.lc_easy, c.lc_medium, c.lc_hard)}</div>
                              : <span className="text-xs text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-3">
                            {ev?.score != null
                              ? <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full', scoreBg(ev.score))}>{ev.score}%</span>
                              : (ev as (Evaluation & { eval_status?: string }))?.eval_status === 'error'
                                ? <span className="text-xs text-red-500">Failed</span>
                                : ev?.recommendation === 'PENDING'
                                ? <span className="text-xs text-gray-400 flex items-center gap-1"><RefreshCw className="w-3 h-3 animate-spin" />…</span>
                                : <span className="text-xs text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-3">
                            {rec
                              ? <span className={cn('badge', rec.cls)}>{rec.label}</span>
                              : <span className="text-xs text-gray-300">—</span>}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-1">
                              {selectedJobId && (
                                <button onClick={() => triggerEvaluation(c.id, selectedJobId as number)}
                                  disabled={evaluating === `${c.id}-${selectedJobId}`}
                                  className="p-1.5 rounded-lg hover:bg-brand-50 text-brand-600 transition-colors" title="Evaluate">
                                  {evaluating === `${c.id}-${selectedJobId}`
                                    ? <RefreshCw className="w-4 h-4 animate-spin" />
                                    : <Zap className="w-4 h-4" />}
                                </button>
                              )}
                              {ev && (
                                <>
                                  <button onClick={() => takeAction(ev.id, ev.recruiter_action === 'shortlisted' ? 'pending' : 'shortlisted')}
                                    disabled={actioning === ev.id}
                                    className={cn('p-1.5 rounded-lg transition-colors',
                                      ev.recruiter_action === 'shortlisted' ? 'text-green-600 bg-green-50' : 'hover:bg-green-50 text-gray-400 hover:text-green-600')}
                                    title="Shortlist">
                                    <CheckCircle2 className="w-4 h-4" />
                                  </button>
                                  <button onClick={() => takeAction(ev.id, ev.recruiter_action === 'rejected' ? 'pending' : 'rejected')}
                                    disabled={actioning === ev.id}
                                    className={cn('p-1.5 rounded-lg transition-colors',
                                      ev.recruiter_action === 'rejected' ? 'text-red-600 bg-red-50' : 'hover:bg-red-50 text-gray-400 hover:text-red-500')}
                                    title="Reject">
                                    <XCircle className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                              <button onClick={() => setMsgModal({ userId: c.user_id, name: c.full_name })}
                                className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors" title="Message">
                                <MessageSquare className="w-4 h-4" />
                              </button>
                              <button onClick={() => openDetail(c)}
                                className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors" title="View profile">
                                <BookOpen className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bulk action bar */}
      <BulkBar
        count={selected.size}
        onShortlist={() => handleBulkAction('shortlisted')}
        onReject={() => handleBulkAction('rejected')}
        onExport={() => exportCSV(filtered.filter(c => selected.has(c.id)))}
        onClear={() => setSelected(new Set())}
        loading={bulkLoading}
      />

      {/* Candidate Detail Modal */}
      <Modal open={!!detailModal} onClose={() => setDetailModal(null)} title="Candidate Profile" size="2xl">
        {detailModal && (
          <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xl font-bold shrink-0">
                {initials(detailModal.candidate.full_name)}
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900">{detailModal.candidate.full_name}</h3>
                <p className="text-sm text-gray-500">{detailModal.candidate.headline}</p>
                <p className="text-xs text-gray-400">{detailModal.candidate.location} · {detailModal.candidate.years_experience} yrs exp</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <Github className="w-4 h-4 text-gray-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-gray-900">{detailModal.candidate.github_repos ?? '—'}</p>
                <p className="text-xs text-gray-500">Repos</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <Code2 className="w-4 h-4 text-orange-500 mx-auto mb-1" />
                <p className="text-lg font-bold text-gray-900">
                  {lcTotal(detailModal.candidate.lc_easy, detailModal.candidate.lc_medium, detailModal.candidate.lc_hard) || '—'}
                </p>
                <p className="text-xs text-gray-500">LeetCode</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-gray-900">
                  {[...detailModal.candidate.skills, ...detailModal.candidate.resume_skills].length}
                </p>
                <p className="text-xs text-gray-500">Skills</p>
              </div>
            </div>

            {[...detailModal.candidate.skills, ...detailModal.candidate.resume_skills].length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {[...new Set([...detailModal.candidate.skills, ...detailModal.candidate.resume_skills])].map(s => (
                    <span key={s} className="text-xs bg-brand-50 text-brand-700 border border-brand-100 px-2 py-0.5 rounded-full">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {detailModal.evaluations.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">AI Evaluations</p>
                <div className="space-y-4">
                  {detailModal.evaluations.map(ev => {
                    const rec    = recommendationBadge(ev.recommendation)
                    const report = detailModal.richFeedback[ev.id]
                    const culturalDNA = normalizeCulturalDNA(ev.cultural_dna, detailModal.candidate.full_name)
                    return (
                      <div key={ev.id} className="border border-gray-200 rounded-xl p-4 space-y-4">
                        <div className="flex items-center gap-3">
                          <ScoreRing score={ev.score} size={48} />
                          <div className="flex-1">
                            <p className="font-medium text-sm text-gray-900">{ev.job?.title}</p>
                            <div className="flex gap-2 mt-1 flex-wrap">
                              <span className={cn('badge', rec.cls)}>{rec.label}</span>
                              <span className={cn('badge',
                                ev.recruiter_action === 'shortlisted' ? 'bg-green-100 text-green-700' :
                                ev.recruiter_action === 'rejected'    ? 'bg-red-100 text-red-600' :
                                                                        'bg-gray-100 text-gray-500')}>
                                {ev.recruiter_action}
                              </span>
                              {ev.nd_inclusion?.nd_flag && (
                                <InclusionBadge
                                  type={ev.nd_inclusion.nd_type}
                                  source={ev.nd_inclusion.nd_source}
                                  size="sm"
                                />
                              )}
                            </div>
                          </div>
                          <div className="flex gap-1 shrink-0">
                            <button onClick={() => takeAction(ev.id, 'shortlisted')}
                              disabled={actioning === ev.id || ev.recruiter_action === 'shortlisted'}
                              className={cn('btn-secondary text-xs px-2 py-1',
                                ev.recruiter_action === 'shortlisted' && 'bg-green-50 border-green-200 text-green-700')}>
                              <CheckCircle2 className="w-3 h-3" /> Shortlist
                            </button>
                            <button onClick={() => takeAction(ev.id, 'rejected')}
                              disabled={actioning === ev.id || ev.recruiter_action === 'rejected'}
                              className={cn('btn-secondary text-xs px-2 py-1',
                                ev.recruiter_action === 'rejected' && 'bg-red-50 border-red-200 text-red-600')}>
                              <XCircle className="w-3 h-3" /> Reject
                            </button>
                          </div>
                        </div>

                        {report?.recruiter_summary && (
                          <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">{report.recruiter_summary}</p>
                        )}
                        {report?.badges?.length > 0 && <BadgeRow badges={report.badges} size="sm" />}
                        {report?.confidence_score && <ConfidenceScoreCard data={report.confidence_score} />}
                        {report?.skill_match_visualization?.required_skills?.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Skill Match</p>
                            <SkillMatchVisualization data={report.skill_match_visualization} compact />
                          </div>
                        )}
                        {culturalDNA && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Cultural DNA</p>
                            <CulturalDNACard
                              data={culturalDNA}
                              candidateName={detailModal.candidate.full_name}
                            />
                          </div>
                        )}
                        {report?.why_not_selected?.reasons?.length > 0 && (
                          <WhyNotSelected data={report.why_not_selected} score={ev.score} />
                        )}
                        {report?.learning_path?.length > 0 && <LearningPath weeks={report.learning_path} />}
                        {!report && (
                          <div className="grid grid-cols-2 gap-3">
                            {ev.strengths?.length > 0 && (
                              <div>
                                <p className="text-xs font-semibold text-green-600 mb-1">Strengths</p>
                                <ul className="space-y-0.5">
                                  {ev.strengths.map((s, i) => <li key={i} className="text-xs text-gray-600">✓ {s}</li>)}
                                </ul>
                              </div>
                            )}
                            {ev.gaps?.length > 0 && (
                              <div>
                                <p className="text-xs font-semibold text-orange-600 mb-1">Gaps</p>
                                <ul className="space-y-0.5">
                                  {ev.gaps.map((g, i) => <li key={i} className="text-xs text-gray-600">△ {g}</li>)}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                        {Array.isArray((ev.feedback_report as unknown as Record<string, unknown>)?.interview_questions) && (
                          <div className="pt-3 border-t border-gray-100">
                            <p className="text-xs font-semibold text-gray-500 mb-2">Interview Questions</p>
                            <ol className="space-y-1">
                              {((ev.feedback_report as unknown as { interview_questions: string[] }).interview_questions).map((q: string, i: number) => (
                                <li key={i} className="text-xs text-gray-600">{i + 1}. {q}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => { setDetailModal(null); setMsgModal({ userId: detailModal.candidate.user_id, name: detailModal.candidate.full_name }) }}
                className="btn-secondary flex-1 justify-center">
                <MessageSquare className="w-4 h-4" /> Message
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Message Modal */}
      <Modal open={!!msgModal} onClose={() => setMsgModal(null)} title={`Message ${msgModal?.name}`} size="md">
        <div className="p-6 space-y-4">
          {/* Message templates */}
          <div>
            <label className="label">Template</label>
            <select className="input" onChange={e => e.target.value && setMsgBody(e.target.value)}>
              <option value="">Choose a template…</option>
              <option value="Hi! We reviewed your application and would love to schedule a quick call. Are you available this week?">
                Interview invite
              </option>
              <option value="Thank you for your interest. After careful review, we've decided to move forward with other candidates at this time. We wish you the best!">
                Polite rejection
              </option>
              <option value="Great news — you've been shortlisted! We'll be in touch shortly with next steps.">
                Shortlist notification
              </option>
              <option value="We'd love to learn more about your experience. Could you share more details about your background?">
                Request more info
              </option>
            </select>
          </div>
          <textarea className="input resize-none w-full" rows={5}
            placeholder="Write your message…"
            value={msgBody} onChange={e => setMsgBody(e.target.value)} />
          <div className="flex gap-3">
            <button onClick={() => setMsgModal(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={sendMessage} disabled={sendingMsg || !msgBody.trim()} className="btn-primary flex-1 justify-center">
              {sendingMsg ? <RefreshCw className="w-4 h-4 animate-spin" /> : null}
              Send Message
            </button>
          </div>
        </div>
      </Modal>

    </RecruiterLayout>
  )
}
