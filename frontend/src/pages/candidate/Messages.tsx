import { useState, useEffect, useRef } from 'react'
import { Send, MessageSquare, RefreshCw } from 'lucide-react'
import CandidateLayout from '@/components/layout/CandidateLayout'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import { cn, timeAgo, initials } from '@/lib/utils'
import type { Message } from '@/types'
import toast from 'react-hot-toast'

interface Thread {
  partnerId: number
  partnerName: string
  messages: Message[]
  unread: number
}

function buildThreads(messages: Message[], myId: number): Thread[] {
  const map = new Map<number, Thread>()
  for (const m of messages) {
    const partnerId = m.sender_id === myId ? m.recipient_id : m.sender_id
    const partnerName = m.sender_id === myId ? (m.recipient_name || 'Unknown') : (m.sender_name || 'Unknown')
    if (!map.has(partnerId)) {
      map.set(partnerId, { partnerId, partnerName, messages: [], unread: 0 })
    }
    const t = map.get(partnerId)!
    t.messages.push(m)
    if (!m.is_read && m.recipient_id === myId) t.unread++
  }
  return Array.from(map.values()).sort((a, b) => {
    const aLast = a.messages[a.messages.length - 1]?.created_at || ''
    const bLast = b.messages[b.messages.length - 1]?.created_at || ''
    return bLast.localeCompare(aLast)
  })
}

export default function CandidateMessages() {
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeThread, setActiveThread] = useState<Thread | null>(null)
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const [loading, setLoading] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchMessages()
    const id = setInterval(fetchMessages, 5000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (user) {
      const t = buildThreads(messages, user.id)
      setThreads(t)
      if (activeThread) {
        const updated = t.find(x => x.partnerId === activeThread.partnerId)
        if (updated) setActiveThread(updated)
      }
    }
  }, [messages, user?.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeThread?.messages])

  async function fetchMessages() {
    try {
      const res = await api.get('/me/messages')
      setMessages(res.data.messages)
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  async function markRead(msg: Message) {
    if (!msg.is_read && msg.recipient_id === user?.id) {
      try { await api.patch(`/messages/${msg.id}/read`) } catch { /* ignore */ }
    }
  }

  async function openThread(thread: Thread) {
    setActiveThread(thread)
    thread.messages.forEach(m => markRead(m))
  }

  async function sendMessage() {
    if (!body.trim() || !activeThread) return
    setSending(true)
    try {
      await api.post('/messages', {
        recipient_id: activeThread.partnerId,
        subject: 'Re: Conversation',
        body: body.trim(),
      })
      setBody('')
      await fetchMessages()
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to send')
    } finally { setSending(false) }
  }

  return (
    <CandidateLayout>
      <div className="flex h-full" style={{ height: 'calc(100vh - 57px)' }}>
        {/* Thread list */}
        <div className="w-72 border-r border-gray-200 bg-white flex flex-col shrink-0">
          <div className="px-4 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Messages</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="w-5 h-5 text-gray-400 animate-spin" />
              </div>
            ) : threads.length === 0 ? (
              <div className="text-center py-8 px-4">
                <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No messages yet</p>
              </div>
            ) : threads.map(t => {
              const last = t.messages[t.messages.length - 1]
              return (
                <div
                  key={t.partnerId}
                  onClick={() => openThread(t)}
                  className={cn(
                    'px-4 py-3 cursor-pointer hover:bg-gray-50 border-b border-gray-50 transition-colors',
                    activeThread?.partnerId === t.partnerId && 'bg-brand-50',
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold shrink-0">
                      {initials(t.partnerName)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className={cn('text-sm truncate', t.unread > 0 ? 'font-semibold text-gray-900' : 'font-medium text-gray-700')}>
                          {t.partnerName}
                        </p>
                        {t.unread > 0 && (
                          <span className="w-5 h-5 bg-brand-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center shrink-0">
                            {t.unread}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 truncate">{last?.body}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Chat area */}
        {activeThread ? (
          <div className="flex-1 flex flex-col bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-5 py-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-xs font-bold">
                {initials(activeThread.partnerName)}
              </div>
              <div>
                <p className="font-semibold text-sm text-gray-900">{activeThread.partnerName}</p>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {activeThread.messages.map(m => (
                <div key={m.id} className={cn('flex', m.is_mine ? 'justify-end' : 'justify-start')}>
                  <div className={cn(
                    'max-w-xs lg:max-w-md px-4 py-2.5 rounded-2xl text-sm',
                    m.is_mine
                      ? 'bg-brand-600 text-white rounded-br-sm'
                      : 'bg-white text-gray-900 border border-gray-200 rounded-bl-sm shadow-sm',
                  )}>
                    <p className="whitespace-pre-wrap">{m.body}</p>
                    <p className={cn('text-[10px] mt-1', m.is_mine ? 'text-brand-200' : 'text-gray-400')}>
                      {timeAgo(m.created_at)}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="bg-white border-t border-gray-200 p-4">
              <div className="flex gap-3">
                <textarea
                  className="input flex-1 resize-none"
                  rows={2}
                  placeholder="Type a message…"
                  value={body}
                  onChange={e => setBody(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
                  }}
                />
                <button
                  onClick={sendMessage}
                  disabled={sending || !body.trim()}
                  className="btn-primary self-end px-4"
                >
                  {sending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center text-gray-400">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Select a conversation</p>
            </div>
          </div>
        )}
      </div>
    </CandidateLayout>
  )
}
