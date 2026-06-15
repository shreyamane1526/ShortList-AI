import { useState, useEffect } from 'react'
import { Zap, X, ExternalLink, Bell, BellOff } from 'lucide-react'
import api from '@/lib/api'
import { cn, timeAgo, scoreBg } from '@/lib/utils'
import toast from 'react-hot-toast'

interface AlertJob {
  id: number
  match_score: number
  alerted_at: string
  job: {
    id: number
    title: string
    company: string
    location: string
    url: string
    tags: string[]
    source: string
  } | null
}

interface Subscription {
  enabled: boolean
  min_match_score: number
}

export default function JobAlertBadge() {
  const [alerts, setAlerts] = useState<AlertJob[]>([])
  const [sub, setSub] = useState<Subscription | null>(null)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAlerts()
    fetchSub()
  }, [])

  async function fetchAlerts() {
    try {
      const res = await api.get('/jobs/alerts')
      setAlerts(res.data.alerts)
    } catch { /* ignore */ }
  }

  async function fetchSub() {
    try {
      const res = await api.get('/jobs/alert/subscription')
      setSub(res.data.subscription)
    } catch { /* ignore */ }
  }

  async function toggleAlerts() {
    if (!sub) return
    setLoading(true)
    try {
      const res = await api.post('/jobs/alert/subscribe', { enabled: !sub.enabled })
      setSub(res.data.subscription)
      toast.success(res.data.subscription.enabled ? 'Job alerts enabled' : 'Job alerts paused')
    } catch {
      toast.error('Failed to update alert settings')
    } finally {
      setLoading(false)
    }
  }

  const count = alerts.length

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
          count > 0
            ? 'bg-brand-50 text-brand-700 border border-brand-200 hover:bg-brand-100'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
        )}
      >
        <Zap className="w-4 h-4" />
        New Matches
        {count > 0 && (
          <span className="bg-brand-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span className="font-semibold text-sm text-gray-900">
              New Job Matches {count > 0 && <span className="text-brand-600">({count})</span>}
            </span>
            <div className="flex items-center gap-2">
              {sub && (
                <button
                  onClick={toggleAlerts}
                  disabled={loading}
                  title={sub.enabled ? 'Pause alerts' : 'Enable alerts'}
                  className="p-1 rounded hover:bg-gray-100 transition-colors"
                >
                  {sub.enabled
                    ? <Bell className="w-4 h-4 text-brand-600" />
                    : <BellOff className="w-4 h-4 text-gray-400" />}
                </button>
              )}
              <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-gray-100">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          </div>

          {/* Alert list */}
          <div className="max-h-[400px] overflow-y-auto divide-y divide-gray-50">
            {alerts.length === 0 ? (
              <div className="py-10 text-center">
                <Zap className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">No new matches since last login</p>
                {sub && !sub.enabled && (
                  <button
                    onClick={toggleAlerts}
                    className="mt-3 text-xs text-brand-600 hover:underline"
                  >
                    Enable alerts to get notified
                  </button>
                )}
              </div>
            ) : alerts.map(a => a.job && (
              <div key={a.id} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-gray-900 truncate">{a.job.title}</span>
                      <span className={cn('text-xs font-bold px-1.5 py-0.5 rounded-full', scoreBg(a.match_score))}>
                        {a.match_score}%
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{a.job.company} · {a.job.location}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{timeAgo(a.alerted_at)}</p>
                    {a.job.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {a.job.tags.slice(0, 4).map(t => (
                          <span key={t} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {a.job.url && (
                    <a
                      href={a.job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 p-1.5 rounded hover:bg-gray-100 transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Footer: subscription settings */}
          {sub && (
            <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                Min match: <strong>{sub.min_match_score}%</strong>
              </span>
              <button
                onClick={toggleAlerts}
                disabled={loading}
                className={cn(
                  'text-xs font-medium px-2.5 py-1 rounded-md transition-colors',
                  sub.enabled
                    ? 'text-red-600 hover:bg-red-50'
                    : 'text-brand-600 hover:bg-brand-50',
                )}
              >
                {sub.enabled ? 'Pause alerts' : 'Enable alerts'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
