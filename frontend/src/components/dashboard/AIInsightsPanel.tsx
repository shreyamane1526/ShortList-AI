import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, BookOpen, Target, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Evaluation } from '@/types'

interface Props {
  evaluations: Evaluation[]
  loading?: boolean
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-14 bg-gray-100 rounded-lg" />
      ))}
    </div>
  )
}

interface Insight {
  icon: React.ReactNode
  title: string
  body: string
  cta?: string
  ctaPath?: string
  color: string
}

export default function AIInsightsPanel({ evaluations, loading }: Props) {
  const navigate = useNavigate()

  if (loading) return <Skeleton />

  const insights: Insight[] = []

  // Derive insights from real evaluation data
  const done = evaluations.filter(e => e.eval_status === 'done')
  const avgScore = done.length
    ? Math.round(done.reduce((s, e) => s + (e.score ?? 0), 0) / done.length)
    : null

  // Collect all gaps across evaluations
  const gapFreq: Record<string, number> = {}
  for (const ev of done) {
    for (const gap of ev.gaps || []) {
      const key = gap.toLowerCase().trim()
      gapFreq[key] = (gapFreq[key] || 0) + 1
    }
  }
  const topGaps = Object.entries(gapFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([g]) => g)

  if (topGaps.length > 0) {
    insights.push({
      icon: <Target className="w-4 h-4" />,
      title: 'Top skill gap to close',
      body: `"${topGaps[0]}" appears in ${gapFreq[topGaps[0]]} of your evaluations. Addressing it could significantly boost your match scores.`,
      cta: 'View Learning Hub',
      ctaPath: '/candidate/learning-hub',
      color: 'text-orange-600 bg-orange-50 border-orange-200',
    })
  }

  if (topGaps.length > 1) {
    insights.push({
      icon: <BookOpen className="w-4 h-4" />,
      title: 'Second priority',
      body: `"${topGaps[1]}" is also frequently missing. Consider a short course or project to demonstrate this skill.`,
      cta: 'Browse Jobs',
      ctaPath: '/candidate/jobs',
      color: 'text-purple-600 bg-purple-50 border-purple-200',
    })
  }

  if (avgScore != null) {
    const msg = avgScore >= 75
      ? `Your average match score is ${avgScore}% — you're a strong candidate. Keep applying!`
      : avgScore >= 50
      ? `Your average match score is ${avgScore}%. Closing your top skill gaps could push you above 75%.`
      : `Your average match score is ${avgScore}%. Focus on roles that better match your current skill set.`

    insights.push({
      icon: <TrendingUp className="w-4 h-4" />,
      title: 'Score insight',
      body: msg,
      cta: 'View Applications',
      ctaPath: '/candidate/applications',
      color: avgScore >= 75 ? 'text-green-600 bg-green-50 border-green-200' :
             avgScore >= 50 ? 'text-yellow-600 bg-yellow-50 border-yellow-200' :
                              'text-red-600 bg-red-50 border-red-200',
    })
  }

  // Shortlist rate
  const shortlisted = evaluations.filter(e => e.recruiter_action === 'shortlisted').length
  if (evaluations.length >= 3 && shortlisted === 0) {
    insights.push({
      icon: <Sparkles className="w-4 h-4" />,
      title: 'Boost your visibility',
      body: 'No shortlists yet. Try completing your profile with GitHub and a resume — recruiters shortlist enriched profiles 3× more often.',
      cta: 'Complete Profile',
      ctaPath: '/candidate/profile',
      color: 'text-brand-600 bg-brand-50 border-brand-200',
    })
  }

  if (insights.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-gray-400">
        <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-30" />
        Complete evaluations to unlock AI insights
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {insights.slice(0, 3).map((ins, i) => (
        <div key={i} className={cn('rounded-xl border p-3.5', ins.color)}>
          <div className="flex items-start gap-2.5">
            <div className="mt-0.5 shrink-0">{ins.icon}</div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold mb-0.5">{ins.title}</p>
              <p className="text-xs opacity-80 leading-relaxed">{ins.body}</p>
              {ins.cta && ins.ctaPath && (
                <button
                  onClick={() => navigate(ins.ctaPath!)}
                  className="mt-2 flex items-center gap-1 text-[10px] font-semibold hover:underline"
                >
                  {ins.cta} <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
