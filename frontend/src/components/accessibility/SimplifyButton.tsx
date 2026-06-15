/**
 * SimplifyButton — calls POST /api/chat/ask to rewrite text in plain English.
 * Renders a small inline button. On success, calls onReplace(simplifiedText).
 */
import { useState } from 'react'
import { Wand2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface Props {
  text: string
  onReplace: (simplified: string) => void
  className?: string
  label?: string
}

export default function SimplifyButton({ text, onReplace, className = '', label = 'Simplify language' }: Props) {
  const [loading, setLoading] = useState(false)

  async function handleSimplify() {
    if (!text?.trim() || loading) return
    setLoading(true)
    const t = toast.loading('Simplifying…')
    try {
      const response = await fetch('/api/chat/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token') ?? ''}`,
        },
        body: JSON.stringify({
          text,
          prompt:
            'Rewrite this in plain simple English, short sentences, no jargon, max 10 words per sentence.',
        }),
      })

      if (!response.ok) throw new Error('Request failed')

      // Handle streaming or plain JSON response
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let full = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          full += decoder.decode(value, { stream: true })
        }
      } else {
        full = await response.text()
      }

      // Try to parse JSON envelope
      let result = full.trim()
      try {
        const j = JSON.parse(full)
        result = j.answer ?? j.result ?? j.text ?? j.response ?? full
      } catch { /* not JSON, use raw */ }

      toast.dismiss(t)
      toast.success('Simplified')
      onReplace(result)
    } catch {
      toast.dismiss(t)
      toast.error('Could not simplify text')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleSimplify}
      disabled={loading || !text?.trim()}
      aria-label={label}
      className={`inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 hover:underline disabled:opacity-40 disabled:cursor-not-allowed transition-colors ${className}`}
    >
      <Wand2 className="w-3 h-3" aria-hidden="true" />
      {loading ? 'Simplifying…' : label}
    </button>
  )
}
