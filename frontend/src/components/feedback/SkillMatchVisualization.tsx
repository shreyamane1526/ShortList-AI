import { cn } from '@/lib/utils'
import type { SkillMatchVisualization as SkillMatchVizType } from '@/types/feedback'
import SimplifyButton from '@/components/accessibility/SimplifyButton'
import { useState } from 'react'

interface Props {
  data: SkillMatchVizType
  compact?: boolean
}

export default function SkillMatchVisualization({ data, compact = false }: Props) {
  const total = data.required_skills?.length ?? 0
  const matched = data.matched?.length ?? 0
  const missing = data.missing?.length ?? 0
  const partial = data.partial?.length ?? 0
  const pct = total > 0 ? Math.round((matched / total) * 100) : 0

  // Accessible score label — never color-only
  const scoreLabel =
    pct >= 70 ? 'Strong match' :
    pct >= 40 ? 'Partial match' :
    'Needs improvement'

  const scoreClass =
    pct >= 70 ? 'text-green-700' :
    pct >= 40 ? 'text-yellow-700' :
    'text-red-700'

  const scoreIcon =
    pct >= 70 ? '✓' :
    pct >= 40 ? '◑' :
    '✗'

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--nd-muted, #6B7280)' }}>
            Skill Coverage
          </span>
          {/* Icon + text label alongside color — never color alone */}
          <span className={cn('text-sm font-bold flex items-center gap-1', scoreClass)} aria-label={`${matched} of ${total} required skills matched — ${scoreLabel}`}>
            <span aria-hidden="true">{scoreIcon}</span>
            <span>{matched}/{total} required</span>
            <span className="text-xs font-normal ml-1">({scoreLabel})</span>
          </span>
        </div>

        {/* Segmented progress bar with aria label */}
        <div
          className="h-3 rounded-full bg-gray-100 overflow-hidden flex"
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Skill coverage: ${pct}%`}
        >
          {total > 0 && (
            <>
              <div
                className="h-full bg-green-500 transition-all duration-500"
                style={{ width: `${(matched / total) * 100}%` }}
              />
              <div
                className="h-full bg-yellow-400 transition-all duration-500"
                style={{ width: `${(partial / total) * 100}%` }}
              />
            </>
          )}
        </div>

        {/* Legend — icon + text, not color alone */}
        <div className="flex items-center gap-4 mt-1.5 text-xs" style={{ color: 'var(--nd-muted, #6B7280)' }}>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" aria-hidden="true" />
            <span>✓ {matched} matched</span>
          </span>
          {partial > 0 && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" aria-hidden="true" />
              <span>◑ {partial} partial</span>
            </span>
          )}
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-gray-200 inline-block" aria-hidden="true" />
            <span>✗ {missing} missing</span>
          </span>
        </div>
      </div>

      {!compact && (
        <>
          {/* Matched skills */}
          {data.matched?.length > 0 && (
            <SkillGroup
              title="Matched skills"
              icon="✓"
              iconClass="text-green-700"
              chipClass="bg-green-50 text-green-700 border-green-200"
              dotClass="bg-green-500"
              skills={data.matched}
            />
          )}

          {/* Partial skills */}
          {data.partial?.length > 0 && (
            <SkillGroup
              title="Partial match"
              icon="◑"
              iconClass="text-yellow-700"
              chipClass="bg-yellow-50 text-yellow-700 border-yellow-200"
              dotClass="bg-yellow-400"
              skills={data.partial}
            />
          )}

          {/* Missing skills */}
          {data.missing?.length > 0 && (
            <SkillGroup
              title="Missing skills"
              icon="✗"
              iconClass="text-red-700"
              chipClass="bg-red-50 text-red-700 border-red-200"
              dotClass="bg-red-400"
              skills={data.missing}
            />
          )}
        </>
      )}
    </div>
  )
}

// ── Skill group with simplify support ────────────────────────────────────────
function SkillGroup({
  title,
  icon,
  iconClass,
  chipClass,
  dotClass,
  skills,
}: {
  title: string
  icon: string
  iconClass: string
  chipClass: string
  dotClass: string
  skills: string[]
}) {
  const [items, setItems] = useState(skills)

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className={cn('text-xs font-semibold uppercase tracking-wide', iconClass)} aria-hidden="true">
          {icon}
        </span>
        <p className={cn('text-xs font-semibold uppercase tracking-wide', iconClass)}>
          {title}
        </p>
        <SimplifyButton
          text={items.join(', ')}
          onReplace={(s) => setItems(s.split(/[,\n]+/).map(x => x.trim()).filter(Boolean))}
          label="Simplify"
          className="ml-auto"
        />
      </div>
      <div className="flex flex-wrap gap-1.5" role="list" aria-label={title}>
        {items.map((skill, i) => (
          <span
            key={i}
            role="listitem"
            className={cn(
              'inline-flex items-center gap-1 text-xs border px-2.5 py-1 rounded-full font-medium',
              chipClass,
            )}
          >
            <span className={cn('w-1.5 h-1.5 rounded-full', dotClass)} aria-hidden="true" />
            {skill}
          </span>
        ))}
      </div>
    </div>
  )
}
