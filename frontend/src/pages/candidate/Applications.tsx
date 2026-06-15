import { useState, useEffect, useCallback, useRef } from 'react'
import { Briefcase, RefreshCw, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import CandidateLayout from '@/components/layout/CandidateLayout'
import Modal from '@/components/ui/Modal'
import ScoreRing from '@/components/ui/ScoreRing'
import AgentStepper, { deriveSteps } from '@/components/AgentStepper'
import WhyNotSelected from '@/components/feedback/WhyNotSelected'
import SkillMatchVisualization from '@/components/feedback/SkillMatchVisualization'
import LearningPath from '@/components/feedback/LearningPath'
import ConfidenceScoreCard from '@/components/feedback/ConfidenceScoreCard'
import ImprovementPlan from '@/components/feedback/ImprovementPlan'
import BadgeRow from '@/components/feedback/BadgeRow'
import ExplainabilityPanel from '@/components/feedback/ExplainabilityPanel'
import ChatWidget from '@/components/feedback/ChatWidget'
import { InclusionBadge } from '@/components/inclusion/InclusionBadge'
import SimplifyButton from '@/components/accessibility/SimplifyButton'
import LiveKitInterviewModal from '@/components/interview/LiveKitInterviewModal'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import { cn, timeAgo, recommendationBadge, actionBadge } from '@/lib/utils'
import type { Evaluation } from '@/types'
import type { RichFeedbackReport } from '@/types/feedback'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'

export default function CandidateApplications() {
  const { user } = useAuth()
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [feedbackModal, setFeedbackModal] = useState<{
    evalId: number
    report: RichFeedbackReport
    evaluation: Evaluation
  } | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [activeChatEval, setActiveChatEval] = useState<Evaluation | null>(null)
  const [loadingFeedback, setLoadingFeedback] = useState<number | null>(null)
  const [showInterview, setShowInterview] = useState(false)
  const [interviewEvalId, setInterviewEvalId] = useState<number | null>(null)
  const [existingInterviews, setExistingInterviews] = useState<Record<number, any>>({})
  const pollIntervals = useRef<Record<number, ReturnType<typeof setInterval>>>({})

  const fetchEvaluations = useCallback(async () => {
    try {
      const res = await api.get('/candidate/evaluations')
      setEvaluations(res.data.evaluations)
      
      // Check for existing interviews for each evaluation using the structured interview system
      const interviews: Record<number, any> = {}
      for (const ev of res.data.evaluations) {
        try {
          const interviewRes = await api.get(`/candidate/interviews/${ev.id}`)
          // 200 means an interview record exists; 404 means none yet (caught below)
          if (interviewRes.status === 200 && interviewRes.data?.interview_id) {
            interviews[ev.id] = interviewRes.data
          }
        } catch {
          // 404 = no interview yet — that's expected and fine
        }
      }
      setExistingInterviews(interviews)
    } catch { /* ignore */ } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchEvaluations() }, [fetchEvaluations])

  // Poll individual pending evaluations
  useEffect(() => {
    const pending = evaluations.filter(e => e.eval_status === 'pending' || e.eval_status === 'running')

    Object.values(pollIntervals.current).forEach(clearInterval)
    pollIntervals.current = {}

    pending.forEach(ev => {
      const interval = setInterval(async () => {
        try {
          const res = await api.get(`/candidate/evaluations/${ev.id}`)
          const updated: Evaluation = res.data.evaluation
          setEvaluations(prev => prev.map(e => e.id === updated.id ? updated : e))
          if (updated.eval_status === 'done') {
            toast.success(`Evaluation complete for ${updated.job?.title || 'job'}!`)
            clearInterval(interval)
            delete pollIntervals.current[ev.id]
          } else if (updated.eval_status === 'error') {
            toast.error(`Evaluation failed: ${updated.eval_error || 'Unknown error'}`)
            clearInterval(interval)
            delete pollIntervals.current[ev.id]
          }
        } catch { /* ignore */ }
      }, 2000)
      pollIntervals.current[ev.id] = interval
    })

    return () => { Object.values(pollIntervals.current).forEach(clearInterval) }
  }, [evaluations])

  // Background poll for recruiter action changes
  useEffect(() => {
    const id = setInterval(fetchEvaluations, 5000)
    return () => clearInterval(id)
  }, [fetchEvaluations])

  async function viewFeedback(ev: Evaluation) {
    setLoadingFeedback(ev.id)
    try {
      const res = await api.get(`/evaluations/${ev.id}/feedback`)
      const raw = res.data
      const report: RichFeedbackReport = raw.why_not_selected
        ? raw
        : {
            why_not_selected: { reasons: [], tone: 'constructive', improvement_hints: [] },
            improvement_plan: { short_term: [], long_term: [] },
            learning_path: [],
            skill_match_visualization: { required_skills: [], matched: [], missing: [], partial: [] },
            confidence_score: { score: ev.score ?? 50, level: 'Medium', factors: [] },
            badges: [],
            candidate_report_markdown: raw.candidate_report || '',
            recruiter_summary: raw.recruiter_summary || '',
            nd_inclusion: raw.nd_inclusion || ev.nd_inclusion || null,
          }
      if (raw.learning_resources) {
        report.learning_resources = raw.learning_resources
        report.task_checklist = raw.task_checklist || []
      }
      if (raw.nd_inclusion) report.nd_inclusion = raw.nd_inclusion
      setFeedbackModal({ evalId: ev.id, report, evaluation: ev })
    } catch (err: any) {
      if (err?.response?.status === 404) {
        toast.error('Feedback not yet generated. Wait for evaluation to complete.')
      } else {
        toast.error('Failed to load feedback')
      }
    } finally { setLoadingFeedback(null) }
  }

  function startInterview(evalId: number) {
    setInterviewEvalId(evalId)
    setShowInterview(true)
  }

  async function withdraw(evalId: number) {
    if (!confirm('Withdraw this application?')) return
    try {
      await api.delete(`/candidate/evaluations/${evalId}`)
      setEvaluations(evs => evs.filter(e => e.id !== evalId))
      toast.success('Application withdrawn')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to withdraw')
    }
  }

  if (loading) return (
    <CandidateLayout>
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" aria-label="Loading applications" />
      </div>
    </CandidateLayout>
  )

  return (
    <CandidateLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--nd-text, #111827)' }}>
              Applications
            </h1>
            <p className="text-sm mt-1" style={{ color: 'var(--nd-muted, #6B7280)' }}>
              {evaluations.length} total · {evaluations.filter(e => e.recruiter_action === 'shortlisted').length} shortlisted
            </p>
          </div>
          <button onClick={fetchEvaluations} className="btn-secondary" aria-label="Refresh applications">
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
            <span>Refresh</span>
          </button>
        </div>

        {evaluations.length === 0 ? (
          <div className="text-center py-16" style={{ color: 'var(--nd-muted, #9CA3AF)' }}>
            <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30" aria-hidden="true" />
            <p className="font-medium">No applications yet</p>
            <p className="text-sm mt-1">Express interest in jobs to get AI-evaluated</p>
          </div>
        ) : (
          <div className="space-y-3">
            {evaluations.map(ev => {
              const rec = recommendationBadge(ev.recommendation)
              const act = actionBadge(ev.recruiter_action)
              const isExpanded = expanded === ev.id
              const isPending = ev.eval_status === 'pending' || ev.eval_status === 'running'
              const isError = ev.eval_status === 'error'
              const steps = deriveSteps(ev.eval_status, ev.current_step)

              return (
                <div key={ev.id} className="card overflow-hidden">
                  <div
                    className="p-5 flex items-center gap-4 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => setExpanded(isExpanded ? null : ev.id)}
                    role="button"
                    tabIndex={0}
                    aria-expanded={isExpanded}
                    aria-label={`${ev.job?.title || 'Job'} application — ${rec.label}`}
                    onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && setExpanded(isExpanded ? null : ev.id)}
                  >
                    <ScoreRing score={ev.score} size={56} />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold" style={{ color: 'var(--nd-text, #111827)' }}>
                          {ev.job?.title || `Job #${ev.job_id}`}
                        </h3>
                        {isPending && (
                          <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                            <RefreshCw className="w-3 h-3 animate-spin" aria-hidden="true" />
                            <span>Evaluating…</span>
                          </span>
                        )}
                        {isError && (
                          <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                            ✗ Failed
                          </span>
                        )}
                      </div>
                      <p className="text-sm" style={{ color: 'var(--nd-muted, #6B7280)' }}>
                        {ev.job?.company_name}
                      </p>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {/* Icon + text label alongside color — never color alone */}
                        <span className={cn('badge', rec.cls)} aria-label={`Recommendation: ${rec.label}`}>
                          <span aria-hidden="true">{rec.icon}</span>
                          <span className="ml-1">{rec.label}</span>
                        </span>
                        <span className={cn('badge', act.cls)} aria-label={`Status: ${act.label}`}>
                          <span aria-hidden="true">{act.icon}</span>
                          <span className="ml-1">{act.label}</span>
                        </span>
                        <span className="text-xs" style={{ color: 'var(--nd-muted, #9CA3AF)' }}>
                          {timeAgo(ev.created_at)}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {ev.eval_status === 'done' && (
                        <>
                          <button
                            onClick={e => { e.stopPropagation(); viewFeedback(ev) }}
                            disabled={loadingFeedback === ev.id}
                            className="btn-secondary text-xs px-3 py-1.5"
                            aria-label={`View AI feedback for ${ev.job?.title || 'this job'}`}
                          >
                            {loadingFeedback === ev.id
                              ? <RefreshCw className="w-3 h-3 animate-spin" aria-hidden="true" />
                              : <Sparkles className="w-3 h-3 text-brand-500" aria-hidden="true" />}
                            <span>AI Feedback</span>
                          </button>
                          <button
                            onClick={e => { e.stopPropagation(); setActiveChatEval(ev); setChatOpen(true) }}
                            className="btn-secondary text-xs px-3 py-1.5"
                            aria-label={`Ask AI about ${ev.job?.title || 'this job'}`}
                          >
                            <span>Ask AI</span>
                          </button>
                          {existingInterviews[ev.id] ? (
                            <button
                              onClick={e => { e.stopPropagation(); startInterview(ev.id) }}
                              className="btn-secondary text-xs px-3 py-1.5"
                              aria-label={`View interview results for ${ev.job?.title || 'this job'}`}
                            >
                              <span>View Interview</span>
                            </button>
                          ) : (
                            <button
                              onClick={e => { e.stopPropagation(); startInterview(ev.id) }}
                              className="btn-primary text-xs px-3 py-1.5"
                              aria-label={`Start AI interview for ${ev.job?.title || 'this job'}`}
                            >
                              <span>Start Interview</span>
                            </button>
                          )}
                        </>
                      )}
                      {isExpanded
                        ? <ChevronUp className="w-4 h-4 text-gray-400" aria-hidden="true" />
                        : <ChevronDown className="w-4 h-4 text-gray-400" aria-hidden="true" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="border-t border-gray-100 p-5 space-y-4" style={{ backgroundColor: 'var(--nd-bg, #F9FAFB)' }}>
                      {/* Real-time agent stepper */}
                      {isPending && (
                        <div className="bg-white rounded-xl border border-brand-100 p-4">
                          <p className="text-sm font-semibold text-brand-900 mb-3">
                            AI pipeline running…
                          </p>
                          <AgentStepper steps={steps} />
                        </div>
                      )}

                      {isError && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700" role="alert">
                          <p className="font-medium">✗ Evaluation failed</p>
                          {ev.eval_error && <p className="text-xs mt-1">{ev.eval_error}</p>}
                        </div>
                      )}

                      {ev.why_fit && (
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--nd-muted, #6B7280)' }}>
                              Why You Fit
                            </p>
                            <SimplifyButton
                              text={ev.why_fit}
                              onReplace={s => setEvaluations(prev => prev.map(p => p.id === ev.id ? { ...p, why_fit: s } : p))}
                            />
                          </div>
                          <p className="text-sm" style={{ color: 'var(--nd-text, #374151)' }}>{ev.why_fit}</p>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-4">
                        {ev.strengths?.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide mb-2 text-green-700">
                              ✓ Strengths
                            </p>
                            <ul className="space-y-1" aria-label="Strengths">
                              {ev.strengths.map((s, i) => (
                                <li key={i} className="text-sm flex items-start gap-1.5" style={{ color: 'var(--nd-text, #374151)' }}>
                                  <span className="text-green-600 mt-0.5 shrink-0" aria-hidden="true">✓</span>
                                  <span className="flex-1">{s}</span>
                                  <SimplifyButton
                                    text={s}
                                    onReplace={ns => setEvaluations(prev => prev.map(p => p.id === ev.id ? { ...p, strengths: p.strengths?.map((x, idx) => idx === i ? ns : x) } : p))}
                                    label="Simplify"
                                  />
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {ev.gaps?.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide mb-2 text-orange-700">
                              △ Skill Gaps
                            </p>
                            <ul className="space-y-1" aria-label="Skill gaps">
                              {ev.gaps.map((g, i) => (
                                <li key={i} className="text-sm flex items-start gap-1.5" style={{ color: 'var(--nd-text, #374151)' }}>
                                  <span className="text-orange-500 mt-0.5 shrink-0" aria-hidden="true">△</span>
                                  <span className="flex-1">{g}</span>
                                  <SimplifyButton
                                    text={g}
                                    onReplace={ns => setEvaluations(prev => prev.map(p => p.id === ev.id ? { ...p, gaps: p.gaps?.map((x, idx) => idx === i ? ns : x) } : p))}
                                    label="Simplify"
                                  />
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* Interview buttons in evaluation detail view */}
                      {ev.eval_status === 'done' && (
                        <div className="flex items-center gap-3 pt-2">
                          {existingInterviews[ev.id] ? (
                            <button
                              onClick={() => startInterview(ev.id)}
                              className="flex items-center gap-2 px-5 py-2.5 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors text-sm"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                              View Interview Results
                            </button>
                          ) : (
                            <button
                              onClick={() => startInterview(ev.id)}
                              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 transition-colors text-sm"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                              </svg>
                              Start AI Interview
                            </button>
                          )}
                          {existingInterviews[ev.id] && (
                            <button
                              onClick={() => startInterview(ev.id)}
                              className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                            >
                              Re-take interview
                            </button>
                          )}
                        </div>
                      )}

                      <div className="flex justify-end">
                        <button
                          onClick={() => withdraw(ev.id)}
                          className="text-xs text-red-500 hover:text-red-700 hover:underline"
                          aria-label={`Withdraw application for ${ev.job?.title || 'this job'}`}
                        >
                          Withdraw application
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Rich Feedback Modal */}
      <Modal
        open={!!feedbackModal}
        onClose={() => setFeedbackModal(null)}
        title="AI Feedback Report"
        size="2xl"
      >
        {feedbackModal && (
          <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <p className="text-sm" style={{ color: 'var(--nd-muted, #6B7280)' }}>
                AI feedback is based on your evaluation and learning path.
              </p>
              <button
                onClick={() => {
                  setActiveChatEval(feedbackModal.evaluation)
                  setChatOpen(true)
                }}
                className="btn-secondary text-sm px-3 py-2"
                aria-label="Ask AI about this feedback report"
              >
                Ask about this report
              </button>
            </div>

            {/* ND inclusion badge */}
            {(feedbackModal.report.nd_inclusion?.nd_flag || feedbackModal.evaluation.nd_inclusion?.nd_flag) && (
              <InclusionBadge
                type={feedbackModal.report.nd_inclusion?.nd_type || feedbackModal.evaluation.nd_inclusion?.nd_type}
                source={feedbackModal.report.nd_inclusion?.nd_source || feedbackModal.evaluation.nd_inclusion?.nd_source}
              />
            )}

            {/* Achievement badges */}
            {feedbackModal.report.badges?.length > 0 && (
              <BadgeRow badges={feedbackModal.report.badges} />
            )}

            {/* Confidence score */}
            {feedbackModal.report.confidence_score && (
              <ConfidenceScoreCard data={feedbackModal.report.confidence_score} />
            )}

            {/* Skill match visualization */}
            {feedbackModal.report.skill_match_visualization?.required_skills?.length > 0 && (
              <div className="card p-5">
                <p className="text-sm font-semibold mb-4" style={{ color: 'var(--nd-text, #111827)' }}>
                  Skill Match
                </p>
                <SkillMatchVisualization data={feedbackModal.report.skill_match_visualization} />
              </div>
            )}

            {/* Why not selected */}
            {feedbackModal.report.why_not_selected?.reasons?.length > 0 && (
              <WhyNotSelected
                data={feedbackModal.report.why_not_selected}
                score={feedbackModal.evaluation.score}
              />
            )}

            {/* Learning path */}
            {(feedbackModal.report.learning_resources || feedbackModal.report.learning_path?.length > 0) && (
              <LearningPath
                learningResources={feedbackModal.report.learning_resources}
                taskChecklist={feedbackModal.report.task_checklist}
              />
            )}

            {/* Improvement plan */}
            {(feedbackModal.report.improvement_plan?.short_term?.length > 0 ||
              feedbackModal.report.improvement_plan?.long_term?.length > 0) && (
              <ImprovementPlan data={feedbackModal.report.improvement_plan} />
            )}

            {/* Explainability panel */}
            <ExplainabilityPanel
              confidenceScore={feedbackModal.report.confidence_score}
            />

            {/* Full markdown report */}
            {feedbackModal.report.candidate_report_markdown && (
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--nd-muted, #6B7280)' }}>
                    Full Report
                  </p>
                  <SimplifyButton
                    text={feedbackModal.report.candidate_report_markdown}
                    onReplace={s => setFeedbackModal(prev => prev ? { ...prev, report: { ...prev.report, candidate_report_markdown: s } } : prev)}
                  />
                </div>
                <div className="prose prose-sm max-w-none" style={{ color: 'var(--nd-text, #374151)' }}>
                  <ReactMarkdown>{feedbackModal.report.candidate_report_markdown}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {activeChatEval && user?.candidate?.id != null && (
        <ChatWidget
          evaluationId={activeChatEval.id}
          candidateId={user.candidate.id}
          jobId={activeChatEval.job_id}
          isOpen={chatOpen}
          onClose={() => setChatOpen(false)}
        />
      )}

      {/* LiveKit Voice Interview Modal */}
      {interviewEvalId && (
        <LiveKitInterviewModal
          evalId={interviewEvalId}
          open={showInterview}
          onClose={() => {
            setShowInterview(false)
            setInterviewEvalId(null)
            // Refresh to check for new interview data
            fetchEvaluations()
          }}
          candidateName={user?.full_name}
          trade={evaluations.find(e => e.id === interviewEvalId)?.job?.title}
          jobId={evaluations.find(e => e.id === interviewEvalId)?.job_id}
        />
      )}
    </CandidateLayout>
  )
}
