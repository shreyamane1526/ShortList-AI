import { cn } from '@/lib/utils'

interface ScoreRingProps {
  score: number | null | undefined
  size?: number
  strokeWidth?: number
  className?: string
}

export default function ScoreRing({ score, size = 64, strokeWidth = 6, className }: ScoreRingProps) {
  const r = (size - strokeWidth) / 2
  const circ = 2 * Math.PI * r
  const pct = score != null ? Math.min(100, Math.max(0, score)) : 0
  const offset = circ - (pct / 100) * circ

  const color = score == null ? '#d1d5db'
    : score >= 80 ? '#16a34a'
    : score >= 60 ? '#ca8a04'
    : '#dc2626'

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <span className="absolute text-sm font-bold" style={{ color }}>
        {score != null ? score : '—'}
      </span>
    </div>
  )
}
