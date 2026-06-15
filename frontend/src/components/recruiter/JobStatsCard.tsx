import { Users, TrendingUp, CheckCircle2, BarChart2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Job, Evaluation } from '@/types'

interface Props {
  job: Job
  evaluations: Evaluation[]
}

export default function JobStatsCard({ job, evaluations }: Props) {
  const jobEvals = evaluations.filter(e => e.job_id === job.id && e.eval_status === 'done')
  const shortlisted = jobEvals.filter(e => e.recruiter_action === 'shortlisted').length
  const avgScore = jobEvals.length
    ? Math.round(jobEvals.reduce((s, e) => s + (e.score ?? 0), 0) / jobEvals.length)
    : null
  const shortlistRate = jobEvals.length
    ? Math.round((shortlisted / jobEvals.length) * 100)
    : null

  const stats = [
    { icon: <Users className="w-3.5 h-3.5" />, label: 'Applicants', value: job.application_count ?? 0, color: 'text-blue-600' },
    { icon: <BarChart2 className="w-3.5 h-3.5" />, label: 'Avg Score', value: avgScore != null ? `${avgScore}%` : '—', color: 'text-purple-600' },
    { icon: <CheckCircle2 className="w-3.5 h-3.5" />, label: 'Shortlisted', value: shortlisted, color: 'text-green-600' },
    { icon: <TrendingUp className="w-3.5 h-3.5" />, label: 'SL Rate', value: shortlistRate != null ? `${shortlistRate}%` : '—', color: 'text-orange-500' },
  ]

  return (
    <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-100">
      {stats.map(s => (
        <div key={s.label} className="text-center">
          <div className={cn('flex items-center justify-center gap-1 mb-0.5', s.color)}>
            {s.icon}
          </div>
          <p className="text-sm font-bold text-gray-900">{s.value}</p>
          <p className="text-[10px] text-gray-500">{s.label}</p>
        </div>
      ))}
    </div>
  )
}
