import { useState, useEffect, useRef } from 'react'
import { Bell, CheckCheck, Briefcase, UserCheck, Star, MessageSquare, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn, timeAgo } from '@/lib/utils'
import api from '@/lib/api'
import type { Notification } from '@/types'

interface Props {
  /** Poll interval in ms (default 10 000) */
  pollInterval?: number
}

function notifIcon(type: string) {
  switch (type) {
    case 'shortlisted':          return <UserCheck className="w-4 h-4 text-green-500" />
    case 'application_received': return <Briefcase className="w-4 h-4 text-brand-500" />
    case 'status_changed':       return <Star className="w-4 h-4 text-yellow-500" />
    case 'message_received':     return <MessageSquare className="w-4 h-4 text-purple-500" />
    default:                     return <Zap className="w-4 h-4 text-gray-400" />
  }
}

export default function NotificationBell({ pollInterval = 10_000 }: Props) {
  const navigate = useNavigate()
  const [notifs, setNotifs] = useState<Notification[]>([])
  const [unread, setUnread] = useState(0)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Fetch + poll
  useEffect(() => {
    fetchNotifs()
    const id = setInterval(fetchNotifs, pollInterval)
    return () => clearInterval(id)
  }, [pollInterval])

  async function fetchNotifs() {
    try {
      const res = await api.get('/me/notifications')
      setNotifs(res.data.notifications)
      setUnread(res.data.unread_count)
    } catch { /* ignore */ }
  }

  async function markAllRead() {
    try {
      await api.patch('/me/notifications/read-all')
      setUnread(0)
      setNotifs(n => n.map(x => ({ ...x, is_read: true })))
    } catch { /* ignore */ }
  }

  async function markOneRead(id: number) {
    try {
      await api.patch(`/me/notifications/${id}/read`)
      setNotifs(n => n.map(x => x.id === id ? { ...x, is_read: true } : x))
      setUnread(u => Math.max(0, u - 1))
    } catch { /* ignore */ }
  }

  function handleClick(n: Notification) {
    if (!n.is_read) markOneRead(n.id)
    setOpen(false)
    if (n.link) navigate(n.link)
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
        aria-label={`Notifications${unread > 0 ? ` (${unread} unread)` : ''}`}
      >
        <Bell className="w-5 h-5 text-gray-600" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 min-w-[16px] h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-0.5">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-gray-900">Notifications</span>
              {unread > 0 && (
                <span className="text-xs bg-red-100 text-red-600 font-bold px-1.5 py-0.5 rounded-full">
                  {unread}
                </span>
              )}
            </div>
            {unread > 0 && (
              <button
                onClick={markAllRead}
                className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-800 transition-colors"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-[360px] overflow-y-auto divide-y divide-gray-50">
            {notifs.length === 0 ? (
              <div className="py-10 text-center">
                <Bell className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">No notifications yet</p>
              </div>
            ) : notifs.map(n => (
              <button
                key={n.id}
                onClick={() => handleClick(n)}
                className={cn(
                  'w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors flex items-start gap-3',
                  !n.is_read && 'bg-blue-50/60',
                )}
              >
                <div className="mt-0.5 shrink-0">
                  {notifIcon(n.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    'text-sm text-gray-900 leading-snug',
                    !n.is_read && 'font-semibold',
                  )}>
                    {n.title}
                  </p>
                  {n.body && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">{timeAgo(n.created_at)}</p>
                </div>
                {!n.is_read && (
                  <div className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
