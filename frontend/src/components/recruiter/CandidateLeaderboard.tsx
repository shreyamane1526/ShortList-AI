import { useNavigate } from 'react-router-dom'
import { Trophy } from 'lucide-react'
import { cn, initials, scoreBg } from '@/lib/utils'
import type { DashboardCandidate } from '@/types'

interface Props {
  candidates: DashboardCandidate[]
  onOpenDetail: (c: DashboardCandidate) => void
}

const MEDALS = ['🥇', '🥈', '🥉']

export default function CandidateLeaderboard({ candidates, onOpenDetail }: Props) {
  const top = candidates
    .filter(c => c.latest_evaluation?.score != null)
    .sort((a, b) => (b.latest_evaluation!.score! - a.latest_evaluation!.score!))
    .slice(0, 5)

  if (top.length === 0) return null

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="w-4 h-4 text-yellow-500" />
        <h3 className="text-sm font-semibold text-gray-700">Top Candidates</h3>
      </div>
      <div className="space-y-2">
        {top.map((c, i) => (
          <button
            key={c.id}
            onClick={() => onOpenDetail(c)}
            className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors text-left"
          >
            <span className="text-base w-6 shrink-0">{MEDALS[i] || `${i + 1}.`}</span>
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
