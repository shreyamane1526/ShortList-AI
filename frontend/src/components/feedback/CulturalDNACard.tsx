/**
 * CulturalDNACard.tsx
 *
 * Displays cultural fit with real‑time animations and live indicator.
 */

import { useMemo, useState, useEffect, type FC } from 'react'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { cn } from '@/lib/utils'

// ============================================================================
// Types
// ============================================================================

export interface CulturalDimension {
  dimension: string
  candidate_score: number
  company_score: number
  match_pct: number
}

export interface CulturalDNAData {
  overall_match_pct: number
  signal_type: string
  candidate_name: string
  company_name: string
  dimensions: CulturalDimension[]
}

// ============================================================================
// Helpers
// ============================================================================

const MATCH_COLORS = {
  high: 'bg-green-100 text-green-700 border-green-200',
  medium: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  low: 'bg-red-50 text-red-600 border-red-200',
} as const

const getMatchColorClass = (pct: number) => {
  if (pct >= 85) return MATCH_COLORS.high
  if (pct >= 65) return MATCH_COLORS.medium
  return MATCH_COLORS.low
}

const formatRadarLabel = (label: string) => {
  const words = label.split(' ')
  return words.length > 2 ? words.slice(0, 2).join(' ') : label
}

// ============================================================================
// Subcomponents
// ============================================================================

const MatchBadge: FC<{ pct: number }> = ({ pct }) => (
  <span
    className={cn(
      'text-xs font-semibold px-2 py-0.5 rounded-full border transition-all duration-300',
      getMatchColorClass(pct)
    )}
  >
    {pct}%
  </span>
)

// Animated comparison bar
const AnimatedComparisonBar: FC<{
  label: string
  score: number
  color: 'purple' | 'blue'
  delay?: number
}> = ({ label, score, color, delay = 0 }) => {
  const [width, setWidth] = useState(0)
  const bgColor = color === 'purple' ? 'bg-purple-400' : 'bg-blue-400'
  const labelColor = color === 'purple' ? 'text-purple-400' : 'text-blue-400'

  useEffect(() => {
    const timer = setTimeout(() => setWidth(score), delay)
    return () => clearTimeout(timer)
  }, [score, delay])

  return (
    <div className="flex items-center gap-2">
      <span className={cn('text-[10px] w-16 shrink-0', labelColor)}>{label}</span>
      <div className="flex-1 bg-gray-700 rounded-full h-1.5 overflow-hidden">
        <div
          className={cn('h-1.5 rounded-full transition-all duration-700 ease-out', bgColor)}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-[10px] text-gray-400 w-6 text-right transition-all duration-300">
        {width}
      </span>
    </div>
  )
}

// Dimension row in signal breakdown (with animated bars)
const DetailedDimensionRow: FC<{ dimension: CulturalDimension; index: number }> = ({
  dimension,
  index,
}) => {
  const { dimension: label, candidate_score, company_score, match_pct } = dimension

  return (
    <div className="bg-gray-800 rounded-lg p-3 transition-all hover:bg-gray-750">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-gray-100">{label}</p>
        <MatchBadge pct={match_pct} />
      </div>
      <p className="text-xs text-gray-400 mb-2">
        Candidate {candidate_score} · Company {company_score}
      </p>
      <div className="space-y-1.5">
        <AnimatedComparisonBar
          label="Candidate"
          score={candidate_score}
          color="purple"
          delay={index * 100}
        />
        <AnimatedComparisonBar
          label="Company"
          score={company_score}
          color="blue"
          delay={index * 100 + 150}
        />
      </div>
    </div>
  )
}

// Compact dimension row for radar tab (no animation needed)
const CompactDimensionRow: FC<{ dimension: CulturalDimension }> = ({ dimension }) => {
  const { dimension: label, candidate_score, company_score, match_pct } = dimension
  return (
    <div className="flex items-center justify-between">
      <div className="flex-1 mr-2">
        <p className="text-xs text-gray-300 font-medium truncate">{label}</p>
        <p className="text-[10px] text-gray-500">
          Candidate {candidate_score} · Company {company_score}
        </p>
      </div>
      <MatchBadge pct={match_pct} />
    </div>
  )
}

// Radar tooltip
const RadarTooltip: FC<any> = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload
  const candidateScore = payload.find((p: any) => p.name === 'Candidate')?.value
  const companyScore = payload.find((p: any) => p.name === 'Company')?.value

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md p-3 text-xs space-y-1 min-w-[160px]">
      <p className="font-semibold text-gray-800 border-b pb-1 mb-1">{data?.fullLabel}</p>
      <div className="flex justify-between gap-4">
        <span className="text-purple-600 font-medium">Candidate:</span>
        <span>{candidateScore}</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-blue-600 font-medium">Company:</span>
        <span>{companyScore}</span>
      </div>
    </div>
  )
}

// Live indicator with pulsing dot and relative timestamp
const LiveIndicator: FC = () => {
  const [timestamp, setTimestamp] = useState('just now')

  useEffect(() => {
    const interval = setInterval(() => {
      setTimestamp('just now')
      // After 5 seconds, change to "5s ago" etc.
      const timer = setTimeout(() => setTimestamp('5s ago'), 5000)
      return () => clearTimeout(timer)
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
      </div>
      <span className="text-green-400 font-medium">LIVE</span>
      <span className="text-gray-500">· updated {timestamp}</span>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export const CulturalDNACard: FC<{
  data: CulturalDNAData
  candidateName: string
}> = ({ data, candidateName }) => {
  const [tab, setTab] = useState<'radar' | 'signal'>('signal') // default to signal for demo
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    // Trigger animations after mount
    setIsVisible(true)
  }, [])

  const radarData = useMemo(
    () =>
      data.dimensions.map(d => ({
        dimension: formatRadarLabel(d.dimension),
        fullLabel: d.dimension,
        Candidate: d.candidate_score,
        Company: d.company_score,
      })),
    [data.dimensions]
  )

  const candidateFirstName = candidateName.split(' ')[0] ?? 'Candidate'

  return (
    <div
      className="border border-gray-200 rounded-xl overflow-hidden bg-gray-900 transition-all duration-500"
      style={{ opacity: isVisible ? 1 : 0, transform: isVisible ? 'translateY(0)' : 'translateY(8px)' }}
    >
      {/* Header with live indicator */}
      <div className="bg-gray-900 px-4 py-3 flex flex-wrap items-center justify-between gap-2 border-b border-gray-800">
        <div>
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">
            Cultural DNA match
          </p>
          <p className="text-xs text-gray-300 mt-0.5">
            {candidateName} — {data.company_name}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <LiveIndicator />
          <div className="flex gap-1 bg-gray-800 rounded-lg p-0.5">
            {(['radar', 'signal'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'text-xs px-3 py-1.5 rounded-md font-medium transition-all focus:outline-none focus:ring-2 focus:ring-purple-500',
                  tab === t
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200'
                )}
              >
                {t === 'radar' ? 'Radar view' : 'Live analysis'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Overall match badge row with animated counter */}
      <div className="bg-gray-800 px-4 py-2 flex flex-wrap items-center gap-3">
        <div className="relative">
          <span className="bg-green-500 text-white text-xs font-bold px-2.5 py-1 rounded-full inline-block">
            {data.overall_match_pct}% overall match
          </span>
          <span className="absolute -top-1 -right-1 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          </span>
        </div>
        <span className="text-xs text-gray-400">{data.signal_type}</span>
      </div>

      {/* Content */}
      <div className="p-4">
        {tab === 'radar' ? (
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1 min-h-[260px]">
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} />
                  <Radar
                    name="Candidate"
                    dataKey="Candidate"
                    stroke="#a78bfa"
                    fill="#a78bfa"
                    fillOpacity={0.25}
                    strokeWidth={2}
                    isAnimationActive
                    animationDuration={1000}
                  />
                  <Radar
                    name="Company"
                    dataKey="Company"
                    stroke="#60a5fa"
                    fill="#60a5fa"
                    fillOpacity={0.15}
                    strokeWidth={2}
                    strokeDasharray="5 3"
                    isAnimationActive
                    animationDuration={1000}
                  />
                  <Tooltip content={<RadarTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
              <div className="flex gap-4 justify-center mt-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-purple-400 inline-block rounded" />
                  <span className="text-xs text-gray-400">{candidateFirstName} (candidate)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-blue-400 inline-block rounded border-dashed" />
                  <span className="text-xs text-gray-400">{data.company_name} (company)</span>
                </div>
              </div>
            </div>
            <div className="md:w-56 space-y-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Dimension scores
              </p>
              {data.dimensions.map(d => (
                <CompactDimensionRow key={d.dimension} dimension={d} />
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Detailed dimension analysis — live updates
            </p>
            {data.dimensions.map((d, idx) => (
              <DetailedDimensionRow key={d.dimension} dimension={d} index={idx} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default CulturalDNACard