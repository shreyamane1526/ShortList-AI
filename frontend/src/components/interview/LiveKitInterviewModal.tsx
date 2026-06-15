/**
 * AI Voice Interview Modal
 *
 * Uses the structured interview system:
 *   POST /candidate/interviews/start        → get interview_id + questions
 *   POST /candidate/interviews/:id/answer   → submit each answer + get assessment
 *   POST /candidate/interviews/:id/complete → finish and persist score
 *
 * LiveKit real-time voice is an optional enhancement. If the token endpoint
 * fails (missing env vars, server error) the interview continues in
 * text + Web Speech API mode — the modal never crashes.
 *
 * Enhanced with:
 * - Role badge & difficulty indicators
 * - Question category display
 * - AI interviewer persona with conversational chat feel
 * - Animated transitions
 * - Confidence meter
 * - Better typography & spacing
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { useAuth } from '@/context/AuthContext'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  evalId: number
  open: boolean
  onClose: () => void
  candidateName?: string
  trade?: string
  jobId?: number
}

interface Question {
  id: number
  question: string
  focus_area: string
}

interface Assessment {
  score: number
  sentiment?: string
  key_point?: string
  feedback?: string
  follow_up_hint?: string
  technical_depth?: number
  clarity?: number
  system_thinking?: number
  communication?: number
}

interface AnsweredQuestion extends Question {
  answer: string
  assessment: Assessment | null
  duration_seconds: number
}

type Phase =
  | 'loading'       // initializing interview
  | 'onboarding'    // show intro before first question
  | 'question'      // answering a question
  | 'submitting'    // waiting for assessment
  | 'complete'      // all questions done
  | 'error'         // unrecoverable error

// ── Helpers ───────────────────────────────────────────────────────────────────

function difficultyColor(difficulty?: string): string {
  switch (difficulty) {
    case 'expert': return 'text-red-600 bg-red-50 border-red-200'
    case 'advanced': return 'text-orange-600 bg-orange-50 border-orange-200'
    case 'intermediate': return 'text-blue-600 bg-blue-50 border-blue-200'
    case 'basic': return 'text-green-600 bg-green-50 border-green-200'
    default: return 'text-gray-600 bg-gray-50 border-gray-200'
  }
}

function domainBadgeColor(domain?: string): string {
  switch ((domain || '').toLowerCase()) {
    case 'frontend': return 'bg-sky-100 text-sky-700 border-sky-200'
    case 'backend': return 'bg-violet-100 text-violet-700 border-violet-200'
    case 'fullstack': return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'devops': return 'bg-rose-100 text-rose-700 border-rose-200'
    case 'ml': return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'mobile': return 'bg-teal-100 text-teal-700 border-teal-200'
    default: return 'bg-indigo-100 text-indigo-700 border-indigo-200'
  }
}

function scoreColor(score: number): string {
  if (score >= 8) return 'text-green-600'
  if (score >= 6) return 'text-yellow-600'
  if (score >= 4) return 'text-orange-600'
  return 'text-red-600'
}

function confidenceMeter(score: number): string {
  if (score >= 8) return 'bg-green-500'
  if (score >= 6) return 'bg-yellow-500'
  if (score >= 4) return 'bg-orange-500'
  return 'bg-red-500'
}

// ── Web Speech API helpers ────────────────────────────────────────────────────

function useSpeechRecognition(onResult: (text: string) => void) {
  const recognitionRef = useRef<any>(null)
  const [listening, setListening] = useState(false)

  const supported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const start = useCallback(() => {
    if (!supported) return
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    const rec = new SR()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'en-US'
    rec.onresult = (e: any) => {
      const transcript = Array.from(e.results as any[])
        .map((r: any) => r[0].transcript)
        .join('')
      onResult(transcript)
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    recognitionRef.current = rec
    rec.start()
    setListening(true)
  }, [supported, onResult])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  useEffect(() => () => recognitionRef.current?.stop(), [])

  return { supported, listening, start, stop }
}

// ── Main component ────────────────────────────────────────────────────────────

export default function LiveKitInterviewModal({
  evalId,
  open,
  onClose,
  candidateName,
  trade,
}: Props) {
  const { user } = useAuth()

  // Interview state
  const [phase, setPhase] = useState<Phase>('loading')
  const [interviewId, setInterviewId] = useState<number | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answered, setAnswered] = useState<AnsweredQuestion[]>([])
  const [answerText, setAnswerText] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [startTime, setStartTime] = useState<number>(0)
  const [lastAssessment, setLastAssessment] = useState<Assessment | null>(null)
  const [jobTitle, setJobTitle] = useState('')

  // Duplicate-init guard (React StrictMode fires effects twice in dev)
  const initializedRef = useRef(false)

  // Speech recognition
  const handleSpeechResult = useCallback((text: string) => {
    setAnswerText(text)
  }, [])
  const { supported: speechSupported, listening, start: startListening, stop: stopListening } =
    useSpeechRecognition(handleSpeechResult)

  // ── Initialize on open ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) {
      initializedRef.current = false
      return
    }
    if (initializedRef.current) return
    initializedRef.current = true

    setPhase('loading')
    setInterviewId(null)
    setQuestions([])
    setCurrentIndex(0)
    setAnswered([])
    setAnswerText('')
    setErrorMsg('')
    setLastAssessment(null)
    setJobTitle('')

    initInterview()
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  async function initInterview() {
    try {
      const res = await api.post('/candidate/interviews/start', {
        evaluation_id: evalId,
      })
      const data = res.data
      setInterviewId(data.interview_id)
      setQuestions(data.questions || [])
      setJobTitle(data.job_title || trade || '')
      setPhase('onboarding')
    } catch (err: any) {
      const status = err?.response?.status
      const msg = err?.response?.data?.error || ''

      if (status === 404) {
        setErrorMsg('Evaluation not found. Please refresh and try again.')
      } else if (status === 403) {
        setErrorMsg('You are not authorized to start this interview.')
      } else if (status === 400) {
        setErrorMsg(msg || 'Could not start interview. Please try again.')
      } else {
        setErrorMsg('Interview service is temporarily unavailable. Please try again in a moment.')
      }
      setPhase('error')
    }
  }

  function beginInterview() {
    setStartTime(Date.now())
    setPhase('question')
  }

  async function submitAnswer() {
    if (!answerText.trim() || interviewId === null) return
    stopListening()

    const q = questions[currentIndex]
    const duration = Math.round((Date.now() - startTime) / 1000)
    setPhase('submitting')

    let assessment: Assessment | null = null
    try {
      const res = await api.post(`/candidate/interviews/${interviewId}/answer`, {
        question_id: q.id,
        answer_text: answerText.trim(),
        duration_seconds: duration,
      })
      assessment = res.data.assessment ?? null
      setLastAssessment(assessment)
    } catch {
      assessment = null
    }

    const answeredQ: AnsweredQuestion = {
      ...q,
      answer: answerText.trim(),
      assessment,
      duration_seconds: duration,
    }
    const newAnswered = [...answered, answeredQ]
    setAnswered(newAnswered)
    setAnswerText('')

    const nextIndex = currentIndex + 1
    if (nextIndex < questions.length) {
      setCurrentIndex(nextIndex)
      setStartTime(Date.now())
      setPhase('question')
    } else {
      await completeInterview(newAnswered)
    }
  }

  async function completeInterview(allAnswered: AnsweredQuestion[]) {
    if (interviewId === null) return
    const scores = allAnswered
      .map(a => a.assessment?.score)
      .filter((s): s is number => s != null)
    const overall = scores.length
      ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
      : null
    const totalDuration = allAnswered.reduce((s, a) => s + a.duration_seconds, 0)

    try {
      await api.post(`/candidate/interviews/${interviewId}/complete`, {
        overall_score: overall,
        duration_seconds: totalDuration,
      })
    } catch {
      // Complete failure is non-fatal — results are already persisted per-answer
    }
    setPhase('complete')
  }

  function handleRetry() {
    initializedRef.current = false
    setPhase('loading')
    setErrorMsg('')
    initInterview()
    initializedRef.current = true
  }

  if (!open) return null

  const currentQuestion = questions[currentIndex]
  const progress = questions.length > 0 ? ((currentIndex) / questions.length) * 100 : 0

  // Derive role domain from trade for badge display
  const roleDomain = (() => {
    const t = (trade || jobTitle || '').toLowerCase()
    if (/frontend|react|vue|angular/.test(t)) return 'Frontend'
    if (/backend|api|spring|django/.test(t)) return 'Backend'
    if (/full.?stack/.test(t)) return 'Full Stack'
    if (/devops|sre|kubernetes/.test(t)) return 'DevOps'
    if (/ml|machine learning|ai|data scientist/.test(t)) return 'ML/AI'
    if (/mobile|android|ios|flutter/.test(t)) return 'Mobile'
    if (/data engineer|etl|pipeline/.test(t)) return 'Data Eng'
    if (/security|pentest|appsec/.test(t)) return 'Security'
    return ''
  })()

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 transition-opacity duration-300"
      role="dialog"
      aria-modal="true"
      aria-label="AI Technical Interview"
    >
      <div className="bg-white rounded-2xl w-full max-w-2xl p-6 relative flex flex-col shadow-2xl border border-gray-100 transition-all duration-300"
           style={{ minHeight: '480px' }}>

        {/* Header with role badge */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div>
              <h2 className="text-xl font-bold text-gray-900 tracking-tight">Technical Interview</h2>
              <p className="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
                {trade || jobTitle ? (
                  <>
                    <span className="font-medium text-gray-500">{trade || jobTitle}</span>
                    {roleDomain && (
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${domainBadgeColor(roleDomain)}`}>
                        {roleDomain}
                      </span>
                    )}
                  </>
                ) : 'Role not specified'}
                <span className="text-gray-300">·</span>
                <span>Priya AI</span>
              </p>
            </div>
          </div>
          <button
            onClick={() => { stopListening(); onClose() }}
            className="text-gray-400 hover:text-gray-600 text-2xl font-light leading-none w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
            aria-label="Close interview"
          >
            ×
          </button>
        </div>

        {/* Progress bar and question metadata */}
        {(phase === 'question' || phase === 'submitting') && questions.length > 0 && (
          <div className="mb-4">
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs font-medium text-gray-400">
                Question {currentIndex + 1} of {questions.length}
              </span>
              <div className="flex items-center gap-2">
                {currentQuestion?.focus_area && (
                  <span className="text-[10px] font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">
                    {currentQuestion.focus_area}
                  </span>
                )}
              </div>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* ── Loading ── */}
        {phase === 'loading' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 animate-in fade-in duration-500">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center animate-pulse shadow-inner">
              <svg className="w-7 h-7 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <p className="text-gray-700 font-semibold">Preparing your interview…</p>
            <p className="text-xs text-gray-400">Generating personalised questions based on your profile</p>
          </div>
        )}

        {/* ── Error ── */}
        {phase === 'error' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-5 animate-in fade-in duration-300">
            <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center border border-red-100">
              <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.963-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="text-center">
              <p className="font-semibold text-gray-800 mb-1">Could not start interview</p>
              <p className="text-sm text-gray-500 max-w-sm leading-relaxed">{errorMsg}</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleRetry}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 font-medium text-sm shadow-sm transition-all"
              >
                Try again
              </button>
              <button
                onClick={onClose}
                className="px-5 py-2.5 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 font-medium text-sm transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ── Onboarding ── */}
        {phase === 'onboarding' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-6 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-200/50">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-1">
                Hi{candidateName ? `, ${candidateName.split(' ')[0]}` : ''}! I'm Priya.
              </h3>
              <p className="text-gray-500 text-sm max-w-sm leading-relaxed">
                I'm a senior technical interviewer and I'll be asking you {questions.length} question{questions.length !== 1 ? 's' : ''} 
                tailored to your profile. There's no time limit — just be yourself.
              </p>
            </div>
            <div className="flex flex-col gap-2.5 text-sm text-gray-500 bg-gray-50 rounded-xl p-4 w-full max-w-sm border border-gray-100">
              {speechSupported && (
                <p className="flex items-center gap-2.5">
                  <span className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-xs">🎙</span>
                  Voice input available — click the mic to speak
                </p>
              )}
              <p className="flex items-center gap-2.5">
                <span className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-xs">⌨️</span>
                Or type your answers directly
              </p>
              <p className="flex items-center gap-2.5">
                <span className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 text-xs">⚡</span>
                Each answer is scored on technical depth & clarity
              </p>
            </div>
            <button
              onClick={beginInterview}
              className="px-8 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:from-indigo-700 hover:to-purple-700 font-semibold text-sm shadow-md shadow-indigo-200/50 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              Start Interview →
            </button>
          </div>
        )}

        {/* ── Question ── */}
        {phase === 'question' && currentQuestion && (
          <div className="flex-1 flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-3 duration-300">
            {/* Question bubble — chat style */}
            <div className="flex gap-3 items-start">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                <span className="text-white font-bold text-xs" aria-hidden="true">P</span>
              </div>
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl rounded-tl-none px-4 py-3 flex-1 border border-indigo-100/50">
                <p className="text-gray-800 text-sm leading-relaxed font-medium">{currentQuestion.question}</p>
              </div>
            </div>

            {/* Confidence meter from last assessment */}
            {lastAssessment && lastAssessment.score != null && (
              <div className="flex items-center gap-2 px-1">
                <span className="text-[10px] font-medium text-gray-400">Last answer:</span>
                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden max-w-24">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${confidenceMeter(lastAssessment.score)}`}
                    style={{ width: `${lastAssessment.score * 10}%` }}
                  />
                </div>
                <span className={`text-[10px] font-bold ${scoreColor(lastAssessment.score)}`}>
                  {lastAssessment.score}/10
                </span>
              </div>
            )}

            {/* Dimension scores from last assessment */}
            {lastAssessment && lastAssessment.technical_depth != null && (
              <div className="flex gap-3 px-1 flex-wrap">
                {[
                  { label: 'Depth', value: lastAssessment.technical_depth },
                  { label: 'Clarity', value: lastAssessment.clarity },
                  { label: 'System', value: lastAssessment.system_thinking },
                  { label: 'Comm', value: lastAssessment.communication },
                ].map(d => d.value != null && (
                  <div key={d.label} className="flex items-center gap-1">
                    <span className="text-[9px] text-gray-400 uppercase tracking-wider">{d.label}</span>
                    <div className="w-10 h-1 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${confidenceMeter(d.value)}`}
                        style={{ width: `${d.value * 10}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Answer area */}
            <div className="flex-1 flex flex-col gap-3 mt-1">
              <textarea
                value={answerText}
                onChange={e => setAnswerText(e.target.value)}
                placeholder="Type your answer here, or use the microphone button to speak…"
                className="flex-1 w-full border border-gray-200 rounded-xl p-3.5 text-sm text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 min-h-28 transition-all placeholder:text-gray-300"
                aria-label="Your answer"
              />

              <div className="flex items-center justify-between gap-3">
                {/* Mic button */}
                {speechSupported ? (
                  <button
                    onClick={listening ? stopListening : startListening}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      listening
                        ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 animate-pulse'
                        : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
                    }`}
                    aria-label={listening ? 'Stop recording' : 'Start voice input'}
                  >
                    <span aria-hidden="true">{listening ? '⏹' : '🎙'}</span>
                    {listening ? 'Recording…' : 'Speak'}
                  </button>
                ) : (
                  <span className="text-[11px] text-gray-400 italic">Voice not supported in this browser</span>
                )}

                <div className="flex items-center gap-2">
                  {lastAssessment && lastAssessment.score != null && currentIndex > 0 && (
                    <span className="text-xs text-gray-400">
                      Score: <strong className={scoreColor(lastAssessment.score)}>{lastAssessment.score}/10</strong>
                    </span>
                  )}
                  <button
                    onClick={submitAnswer}
                    disabled={!answerText.trim()}
                    className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:from-indigo-700 hover:to-purple-700 disabled:opacity-40 disabled:cursor-not-allowed font-medium text-sm transition-all shadow-sm"
                  >
                    {currentIndex + 1 < questions.length ? 'Submit →' : 'Finish'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Submitting ── */}
        {phase === 'submitting' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 animate-in fade-in duration-200">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center animate-spin border-2 border-indigo-200 border-t-indigo-500">
            </div>
            <p className="text-gray-700 font-medium">Analysing your answer…</p>
            <p className="text-xs text-gray-400">Evaluating technical depth, clarity, and relevance</p>
          </div>
        )}

        {/* ── Complete ── */}
        {phase === 'complete' && (
          <InterviewComplete
            answered={answered}
            candidateName={candidateName}
            onClose={onClose}
          />
        )}
      </div>
    </div>
  )
}

// ── Results screen ────────────────────────────────────────────────────────────

interface CompleteProps {
  answered: AnsweredQuestion[]
  candidateName?: string
  onClose: () => void
}

function InterviewComplete({ answered, candidateName, onClose }: CompleteProps) {
  const scores = answered
    .map(a => a.assessment?.score)
    .filter((s): s is number => s != null)
  const avg = scores.length
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1)
    : null

  const depthScores = answered
    .map(a => a.assessment?.technical_depth)
    .filter((s): s is number => s != null)
  const avgDepth = depthScores.length
    ? (depthScores.reduce((a, b) => a + b, 0) / depthScores.length).toFixed(1)
    : null

  const clarityScores = answered
    .map(a => a.assessment?.clarity)
    .filter((s): s is number => s != null)
  const avgClarity = clarityScores.length
    ? (clarityScores.reduce((a, b) => a + b, 0) / clarityScores.length).toFixed(1)
    : null

  function downloadTranscript() {
    const lines = answered.map((a, i) =>
      [
        `Q${i + 1} [${a.focus_area}]: ${a.question}`,
        `Answer: ${a.answer}`,
        a.assessment ? [
          `Score: ${a.assessment.score}/10`,
          a.assessment.technical_depth != null ? `  Technical Depth: ${a.assessment.technical_depth}/10` : '',
          a.assessment.clarity != null ? `  Clarity: ${a.assessment.clarity}/10` : '',
          a.assessment.feedback ? `  Feedback: ${a.assessment.feedback}` : '',
          a.assessment.follow_up_hint ? `  Hint: ${a.assessment.follow_up_hint}` : '',
        ].filter(Boolean).join('\n') : '',
        '',
      ].join('\n')
    )
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'interview-transcript.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex-1 flex flex-col gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Summary header */}
      <div className="text-center">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-green-100 to-emerald-100 flex items-center justify-center mx-auto mb-3 border border-green-200">
          <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-xl font-bold text-gray-900">
          Interview Complete{candidateName ? `, ${candidateName.split(' ')[0]}` : ''}!
        </h3>
        <p className="text-gray-400 text-xs mt-1">Thank you for your time</p>
      </div>

      {/* Score summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gradient-to-b from-indigo-50 to-transparent rounded-xl p-3 text-center border border-indigo-100">
          <p className="text-2xl font-bold text-indigo-700">{avg ?? '—'}</p>
          <p className="text-[10px] text-gray-500 mt-0.5 uppercase tracking-wider">Overall</p>
        </div>
        <div className="bg-gradient-to-b from-amber-50 to-transparent rounded-xl p-3 text-center border border-amber-100">
          <p className="text-2xl font-bold text-amber-700">{avgDepth ?? '—'}</p>
          <p className="text-[10px] text-gray-500 mt-0.5 uppercase tracking-wider">Depth</p>
        </div>
        <div className="bg-gradient-to-b from-emerald-50 to-transparent rounded-xl p-3 text-center border border-emerald-100">
          <p className="text-2xl font-bold text-emerald-700">{avgClarity ?? '—'}</p>
          <p className="text-[10px] text-gray-500 mt-0.5 uppercase tracking-wider">Clarity</p>
        </div>
      </div>

      {/* Per-question scores */}
      {answered.length > 0 && (
        <div className="flex gap-2 flex-wrap justify-center" aria-label="Question scores">
          {answered.map((a, i) => {
            const s = a.assessment?.score
            return (
              <div
                key={i}
                className={`w-9 h-9 rounded-full text-xs flex items-center justify-center font-bold border ${
                  s == null
                    ? 'bg-gray-50 text-gray-400 border-gray-200'
                    : s >= 7
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : s >= 5
                    ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
                    : 'bg-red-50 text-red-700 border-red-200'
                }`}
                title={`Q${i + 1} (${a.focus_area}): ${a.question}`}
                aria-label={`Question ${i + 1}: ${s != null ? `${s}/10` : 'not scored'}`}
              >
                {s ?? '—'}
              </div>
            )
          })}
        </div>
      )}

      {/* Transcript preview */}
      <div
        className="flex-1 overflow-y-auto space-y-3 max-h-44 bg-gray-50 rounded-xl p-4 border border-gray-100"
        aria-label="Interview transcript"
      >
        {answered.map((a, i) => (
          <div key={i} className="text-sm border-b border-gray-100 pb-3 last:border-0 last:pb-0">
            <p className="font-semibold text-indigo-700 mb-0.5 text-xs">
              Q{i + 1} <span className="text-gray-400 font-normal">· {a.focus_area}</span>
            </p>
            <p className="text-gray-800 text-xs leading-relaxed mb-1">{a.question}</p>
            <p className="text-gray-600 text-xs leading-relaxed mb-1 italic">"{a.answer}"</p>
            {a.assessment?.feedback && (
              <p className="text-[11px] text-gray-400">{a.assessment.feedback}</p>
            )}
            {a.assessment?.follow_up_hint && a.assessment.score != null && a.assessment.score < 8 && (
              <p className="text-[11px] text-indigo-400 mt-0.5">💡 {a.assessment.follow_up_hint}</p>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-3 justify-center">
        {answered.length > 0 && (
          <button
            onClick={downloadTranscript}
            className="px-5 py-2.5 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 text-sm font-medium transition-all"
          >
            Download Transcript
          </button>
        )}
        <button
          onClick={onClose}
          className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:from-indigo-700 hover:to-purple-700 text-sm font-medium transition-all shadow-sm"
        >
          Done
        </button>
      </div>
    </div>
  )
}
