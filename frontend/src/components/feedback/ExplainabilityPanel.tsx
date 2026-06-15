import { useState } from 'react'
import { BarChart2, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ConfidenceScore } from '@/types/feedback'

interface Props {
  confidenceScore?: ConfidenceScore
  // Raw pipeline scores for breakdown
  overallFitScore?: number | null   // 0-1 from Agent 2
  trustScore?: number | null        // 0-100 from Agent 1
  reasoningScore?: number | null    // 0-100 from Agent 3
  compositeScore?: number | null    // 0-100 from Agent 4
}

interface Bar {
  label: string
  value: number
  color: string
  description: string
}

export default function ExplainabilityPanel({
  confidenceScore,
  overallFitScore,
  trustScore,
  reasoningScore,
  compositeScore,
}: Props) {
  const [open, setOpen] = useState(false)

  const bars: Bar[] = []

  if (overallFitScore != null) {
    bars.push({
      label: 'Skill Match',
      value: Math.round(overallFitScore * 100),
      color: 'bg-brand-500',
      description: 'How well your skills match the job requirements (Agent 2)',
    })
  }
  if (trustScore != null) {
    bars.push({
      label: 'Evidence Trust',
      value: trustScore,
      color: 'bg-green-500',
      description: 'Integrity of your GitHub/portfolio evidence (Agent 1)',
    })
  }
  if (reasoningScore != null) {
    bars.push({
      label: 'Reasoning Score',
      value: reasoningScore,
      color: 'bg-purple-500',
      description: 'AI hiring analyst score based on all evidence (Agent 3)',
    })
  }
  if (compositeScore != null) {
    bars.push({
      label: 'Composite Score',
      value: Math.round(compositeScore),
      color: 'bg-orange-500',
      description: 'Final weighted score: 45% reasoning + 30% fit + 15% trust + 10% ND uplift (Agent 4)',
    })
  }

  if (bars.length === 0 && !confidenceScore?.factors?.length) return null

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center shrink-0">
            <BarChart2 className="w-4 h-4 text-gray-600" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm">Score Breakdown</p>
            <p className="text-xs text-gray-500 mt-0.5">Why your score is what it is</p>
          </div>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
          : <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />}
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4">
          {bars.map(bar => (
            <div key={bar.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">{bar.label}</span>
                <span className={cn(
                  'text-sm font-bold',
                  bar.value >= 70 ? 'text-green-600' : bar.value >= 40 ? 'text-yellow-600' : 'text-red-500',
                )}>
                  {bar.value}%
                </span>
              </div>
              <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-700', bar.color)}
                  style={{ width: `${bar.value}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">{bar.description}</p>
            </div>
          ))}

          {/* Confidence factors */}
          {confidenceScore?.factors?.length ? (
            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Key factors
              </p>
              <ul className="space-y-1">
                {confidenceScore.factors.map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs text-gray-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
