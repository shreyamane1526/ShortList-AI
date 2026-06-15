import { AlertTriangle, Lightbulb, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { WhyNotSelected as WhyNotSelectedType } from '@/types/feedback'

interface Props {
  data: WhyNotSelectedType
  score?: number | null
}

export default function WhyNotSelected({ data, score }: Props) {
  const [open, setOpen] = useState(true)

  // Only show if score is low or recommendation is negative
  const shouldShow = !score || score < 70

  if (!shouldShow && !data.reasons?.length) return null

  return (
    <div className="rounded-xl border border-orange-200 bg-orange-50 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-orange-100/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-4 h-4 text-orange-600" />
          </div>
          <div>
            <p className="font-semibold text-orange-900 text-sm">Why you weren't selected</p>
            <p className="text-xs text-orange-700 mt-0.5">
              {data.reasons?.length ?? 0} reason{data.reasons?.length !== 1 ? 's' : ''} · constructive feedback
            </p>
          </div>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-orange-500 shrink-0" />
          : <ChevronDown className="w-4 h-4 text-orange-500 shrink-0" />}
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4">
          {/* Reasons */}
          {data.reasons?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-orange-800 uppercase tracking-wide mb-2">
                Key reasons
              </p>
              <ul className="space-y-2">
                {data.reasons.map((reason, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="mt-0.5 w-5 h-5 rounded-full bg-orange-200 text-orange-700 text-xs font-bold flex items-center justify-center shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-sm text-orange-900">{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Improvement hints */}
          {data.improvement_hints?.length > 0 && (
            <div className="bg-white rounded-lg border border-orange-100 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="w-4 h-4 text-amber-500" />
                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Quick wins to improve
                </p>
              </div>
              <ul className="space-y-1.5">
                {data.improvement_hints.map((hint, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-amber-500 mt-0.5 shrink-0">→</span>
                    {hint}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
