import { Info } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { ConfidenceScore } from '@/types/feedback'

interface Props {
  data: ConfidenceScore
}

const LEVEL_CONFIG = {
  High:   { color: 'text-green-700',  bg: 'bg-green-50',  border: 'border-green-200', bar: 'bg-green-500',  ring: 'ring-green-200' },
  Medium: { color: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-200', bar: 'bg-yellow-400', ring: 'ring-yellow-200' },
  Low:    { color: 'text-red-600',    bg: 'bg-red-50',    border: 'border-red-200',   bar: 'bg-red-400',    ring: 'ring-red-200' },
}

export default function ConfidenceScoreCard({ data }: Props) {
  const [showTooltip, setShowTooltip] = useState(false)
  const cfg = LEVEL_CONFIG[data.level] ?? LEVEL_CONFIG.Medium

  return (
    <div className={cn('rounded-xl border p-4', cfg.bg, cfg.border)}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
            Confidence Score
          </p>
          <div className="relative">
            <button
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              onFocus={() => setShowTooltip(true)}
              onBlur={() => setShowTooltip(false)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="What is confidence score?"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
            {showTooltip && (
              <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-56 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 z-10 shadow-lg">
                Weighted combination of evidence trust (30%), fairness score (20%), and skill fit (50%).
                <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900" />
              </div>
            )}
          </div>
        </div>
        <span className={cn('text-xs font-bold px-2.5 py-1 rounded-full border', cfg.color, cfg.bg, cfg.border)}>
          {data.level}
        </span>
      </div>

      {/* Score + bar */}
      <div className="flex items-center gap-3 mb-3">
        <span className={cn('text-3xl font-bold', cfg.color)}>{data.score}</span>
        <div className="flex-1">
          <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all duration-700', cfg.bar)}
              style={{ width: `${data.score}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">out of 100</p>
        </div>
      </div>

      {/* Factors */}
      {data.factors?.length > 0 && (
        <div className="space-y-1">
          {data.factors.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
              <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', cfg.bar)} />
              {f}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
