import { Target, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { ImprovementPlan as ImprovementPlanType } from '@/types/feedback'

interface Props {
  data: ImprovementPlanType
}

export default function ImprovementPlan({ data }: Props) {
  const [open, setOpen] = useState(false)

  if (!data.short_term?.length && !data.long_term?.length) return null

  return (
    <div className="rounded-xl border border-purple-200 bg-purple-50 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-purple-100/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center shrink-0">
            <Target className="w-4 h-4 text-purple-600" />
          </div>
          <div>
            <p className="font-semibold text-purple-900 text-sm">Improvement Plan</p>
            <p className="text-xs text-purple-700 mt-0.5">
              {data.short_term?.length ?? 0} short-term · {data.long_term?.length ?? 0} long-term goals
            </p>
          </div>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-purple-500 shrink-0" />
          : <ChevronDown className="w-4 h-4 text-purple-500 shrink-0" />}
      </button>

      {open && (
        <div className="px-5 pb-5 grid sm:grid-cols-2 gap-4">
          {/* Short term */}
          {data.short_term?.length > 0 && (
            <div className="bg-white rounded-xl border border-purple-100 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-4 h-4 text-purple-500" />
                <p className="text-xs font-semibold text-purple-700 uppercase tracking-wide">
                  Short-term (1–3 months)
                </p>
              </div>
              <ul className="space-y-2">
                {data.short_term.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-purple-400 mt-0.5 shrink-0 font-bold">{i + 1}.</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Long term */}
          {data.long_term?.length > 0 && (
            <div className="bg-white rounded-xl border border-purple-100 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-indigo-500" />
                <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
                  Long-term (3–12 months)
                </p>
              </div>
              <ul className="space-y-2">
                {data.long_term.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-indigo-400 mt-0.5 shrink-0 font-bold">{i + 1}.</span>
                    {item}
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
