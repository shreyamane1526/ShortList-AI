import { useNavigate } from 'react-router-dom'
import { RefreshCw, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { cn, scoreBg, timeAgo } from '@/lib/utils'
import type { Evaluation } from '@/types'

interface Props {
  evaluations: Evaluation[]
}

interface Column {
  id: string
  label: string
  color: string
  headerBg: string
  icon: React.ReactNode
  items: Evaluation[]
}

export default function JobTrackerKanban({ evaluations }: Props) {
  const navigate = useNavigate()

  const applied     = evaluations.filter(e => e.recruiter_action === 'pending' && e.eval_status !== 'done')
  const evaluating  = evaluations.filter(e => e.eval_status === 'done' && e.recruiter_action === 'pending')
  const shortlisted = evaluations.filter(e => e.recruiter_action === 'shortlisted')
  const rejected    = evaluations.filter(e => e.recruiter_action === 'rejected')

  const columns: Column[] = [
    {
      id: 'applied',
      label: 'Applied',
      color: 'text-blue-700',
      headerBg: 'bg-blue-50 border-blue-200',
      icon: <Clock className="w-3.5 h-3.5 text-blue-500" />,
      items: applied,
    },
    {
      id: 'evaluating',
      label: 'Evaluated',
      color: 'text-yellow-700',
      headerBg: 'bg-yellow-50 border-yellow-200',
      icon: <RefreshCw className="w-3.5 h-3.5 text-yellow-500" />,
      items: evaluating,
    },
    {
      id: 'shortlisted',
      label: 'Shortlisted',
      color: 'text-green-700',
      headerBg: 'bg-green-50 border-green-200',
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />,
      items: shortlisted,
    },
    {
      id: 'rejected',
      label: 'Not Selected',
      color: 'text-red-600',
      headerBg: 'bg-red-50 border-red-200',
      icon: <XCircle className="w-3.5 h-3.5 text-red-400" />,
      items: rejected,
    },
  ]

  if (evaluations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        No applications yet — express interest in jobs to get started
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {columns.map(col => (
        <div key={col.id} className="flex flex-col gap-2">
          {/* Column header */}
          <div className={cn('flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-semibold', col.headerBg, col.color)}>
            {col.icon}
            {col.label}
            <span className="ml-auto bg-white/70 px-1.5 py-0.5 rounded-full text-[10px] font-bold">
              {col.items.length}
            </span>
          </div>

          {/* Cards */}
          <div className="space-y-2 min-h-[60px]">
            {col.items.length === 0 ? (
              <div className="text-center py-4 text-xs text-gray-300 border border-dashed border-gray-200 rounded-lg">
                None
              </div>
            ) : col.items.slice(0, 4).map(ev => (
              <button
                key={ev.id}
                onClick={() => navigate('/candidate/applications')}
                className="w-full text-left bg-white border border-gray-200 rounded-lg p-3 hover:border-brand-300 hover:shadow-sm transition-all"
              >
                <p className="text-xs font-semibold text-gray-900 truncate leading-tight">
                  {ev.job?.title || `Job #${ev.job_id}`}
                </p>
                <p className="text-[10px] text-gray-500 truncate mt-0.5">{ev.job?.company_name}</p>
                <div className="flex items-center justify-between mt-2">
                  {ev.score != null ? (
                    <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded', scoreBg(ev.score))}>
                      {ev.score}%
                    </span>
                  ) : (
                    <span className="text-[10px] text-gray-400">—</span>
                  )}
                  <span className="text-[10px] text-gray-400">{timeAgo(ev.created_at)}</span>
                </div>
              </button>
            ))}
            {col.items.length > 4 && (
              <button
                onClick={() => navigate('/candidate/applications')}
                className="w-full text-center text-[10px] text-brand-600 hover:underline py-1"
              >
                +{col.items.length - 4} more
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
