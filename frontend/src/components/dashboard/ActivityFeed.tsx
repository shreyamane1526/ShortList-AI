import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2, XCircle, Clock, Zap, Bell, RefreshCw,
} from 'lucide-react'
import { cn, timeAgo } from '@/lib/utils'
import type { Evaluation, Notification } from '@/types'

interface Props {
  evaluations: Evaluation[]
  notifications: Notification[]
  loading?: boolean
}

interface FeedItem {
  id: string
  icon: React.ReactNode
  iconBg: string
  text: string
  sub?: string
  time: string
  path?: string
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="flex gap-3">
          <div className="w-7 h-7 rounded-full bg-gray-200 shrink-0" />
          <div className="flex-1 space-y-1.5 pt-1">
            <div className="h-3 bg-gray-200 rounded w-3/4" />
            <div className="h-2.5 bg-gray-100 rounded w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ActivityFeed({ evaluations, notifications, loading }: Props) {
  const navigate = useNavigate()

  if (loading) return <Skeleton />

  const items: FeedItem[] = []

  // Build feed from evaluations
  for (const ev of evaluations.slice(0, 6)) {
    const jobTitle = ev.job?.title || `Job #${ev.job_id}`
    const company  = ev.job?.company_name || ''

    if (ev.recruiter_action === 'shortlisted') {
      items.push({
        id: `ev-sl-${ev.id}`,
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
        iconBg: 'bg-green-100 text-green-600',
        text: `Shortlisted for ${jobTitle}`,
        sub: company,
        time: ev.action_taken_at || ev.updated_at,
        path: '/candidate/applications',
      })
    } else if (ev.recruiter_action === 'rejected') {
      items.push({
        id: `ev-rj-${ev.id}`,
        icon: <XCircle className="w-3.5 h-3.5" />,
        iconBg: 'bg-red-100 text-red-500',
        text: `Not selected for ${jobTitle}`,
        sub: company,
        time: ev.action_taken_at || ev.updated_at,
        path: '/candidate/applications',
      })
    } else if (ev.eval_status === 'done' && ev.score != null) {
      items.push({
        id: `ev-done-${ev.id}`,
        icon: <Zap className="w-3.5 h-3.5" />,
        iconBg: 'bg-brand-100 text-brand-600',
        text: `Evaluated for ${jobTitle} — ${ev.score}% match`,
        sub: company,
        time: ev.evaluated_at || ev.updated_at,
        path: '/candidate/applications',
      })
    } else if (ev.eval_status === 'pending' || ev.eval_status === 'running') {
      items.push({
        id: `ev-pend-${ev.id}`,
        icon: <RefreshCw className="w-3.5 h-3.5 animate-spin" />,
        iconBg: 'bg-blue-100 text-blue-500',
        text: `Evaluation running for ${jobTitle}`,
        sub: company,
        time: ev.created_at,
        path: '/candidate/applications',
      })
    } else {
      items.push({
        id: `ev-new-${ev.id}`,
        icon: <Clock className="w-3.5 h-3.5" />,
        iconBg: 'bg-gray-100 text-gray-500',
        text: `Applied to ${jobTitle}`,
        sub: company,
        time: ev.created_at,
        path: '/candidate/applications',
      })
    }
  }

  // Merge in notifications (deduplicated by type)
  for (const n of notifications.slice(0, 4)) {
    items.push({
      id: `notif-${n.id}`,
      icon: <Bell className="w-3.5 h-3.5" />,
      iconBg: n.is_read ? 'bg-gray-100 text-gray-400' : 'bg-brand-100 text-brand-600',
      text: n.title,
      sub: n.body || undefined,
      time: n.created_at,
      path: n.link || undefined,
    })
  }

  // Sort by time descending
  items.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())

  if (items.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-gray-400">
        <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
        No recent activity
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.slice(0, 8).map(item => (
        <button
          key={item.id}
          onClick={() => item.path && navigate(item.path)}
          className={cn(
            'w-full flex items-start gap-3 text-left rounded-lg p-2 transition-colors',
            item.path ? 'hover:bg-gray-50 cursor-pointer' : 'cursor-default',
          )}
        >
          <div className={cn('w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5', item.iconBg)}>
            {item.icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-900 leading-snug">{item.text}</p>
            {item.sub && <p className="text-[10px] text-gray-500 truncate mt-0.5">{item.sub}</p>}
          </div>
          <span className="text-[10px] text-gray-400 shrink-0 mt-0.5">{timeAgo(item.time)}</span>
        </button>
      ))}
    </div>
  )
}
