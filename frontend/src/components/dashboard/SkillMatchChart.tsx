import { useState, useEffect } from 'react'
import { CheckCircle2, XCircle, MinusCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Evaluation } from '@/types'

interface Props {
  evaluations: Evaluation[]
  candidateSkills: string[]
  loading?: boolean
}

interface SkillRow {
  skill: string
  score: number          // 0–100
  matched: number        // times matched
  total: number          // times required
  status: 'strong' | 'partial' | 'missing'
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-3 bg-gray-200 rounded w-2/5" />
      {[90, 70, 55, 30, 10].map(w => (
        <div key={w} className="flex items-center gap-3">
          <div className="h-2.5 bg-gray-200 rounded w-16" />
          <div className="flex-1 h-2.5 bg-gray-100 rounded-full" style={{ maxWidth: `${w}%` }} />
          <div className="h-2.5 bg-gray-200 rounded w-8" />
        </div>
      ))}
    </div>
  )
}

function statusIcon(status: SkillRow['status']) {
  if (status === 'strong')  return <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
  if (status === 'partial') return <MinusCircle  className="w-3.5 h-3.5 text-yellow-500 shrink-0" />
  return                           <XCircle      className="w-3.5 h-3.5 text-red-400 shrink-0" />
}

function barGradient(status: SkillRow['status']) {
  if (status === 'strong')  return 'from-green-400 to-emerald-500'
  if (status === 'partial') return 'from-yellow-400 to-amber-400'
  return                           'from-red-300 to-red-400'
}

function statusLabel(status: SkillRow['status']) {
  if (status === 'strong')  return { text: 'Strong',  cls: 'bg-green-50 text-green-700 border-green-200' }
  if (status === 'partial') return { text: 'Partial', cls: 'bg-yellow-50 text-yellow-700 border-yellow-200' }
  return                           { text: 'Missing', cls: 'bg-red-50 text-red-600 border-red-200' }
}

export default function SkillMatchChart({ evaluations, candidateSkills, loading }: Props) {
  // ALL hooks must come before any conditional return
  const [filterStatus, setFilterStatus] = useState<'all' | 'strong' | 'partial' | 'missing'>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString())
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => setLastUpdated(new Date().toLocaleTimeString()), 30000)
    return () => clearInterval(interval)
  }, [])

  // Now safe to return early after all hooks are declared
  if (loading) return <Skeleton />

  // Build skill frequency map from all jobs the candidate applied to
  const skillFreq: Record<string, { total: number; matched: number }> = {}
  const candidateLower = candidateSkills.map(s => s.toLowerCase())

  // Weighted by recency
  const sortedEvals = evaluations.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  for (let i = 0; i < sortedEvals.length; i++) {
    const ev = sortedEvals[i]
    const weight = Math.max(0.5, 1 - i * 0.1)
    for (const skill of (ev.job?.skills_required || [])) {
      const key = skill.toLowerCase().trim()
      if (!key) continue
      if (!skillFreq[key]) skillFreq[key] = { total: 0, matched: 0 }
      skillFreq[key].total += weight
      if (candidateLower.some(cs => cs.includes(key) || key.includes(cs))) {
        skillFreq[key].matched += weight
      }
    }
  }

  const rows: SkillRow[] = Object.entries(skillFreq)
    .map(([skill, { total, matched }]) => {
      const score = total > 0 ? Math.round((matched / total) * 100) : 0
      const status: SkillRow['status'] = score >= 75 ? 'strong' : score >= 30 ? 'partial' : 'missing'
      return {
        skill: skill.charAt(0).toUpperCase() + skill.slice(1),
        score,
        matched,
        total,
        status,
      }
    })
    .sort((a, b) => b.score - a.score)

  const filteredRows = rows.filter(row => {
    if (filterStatus !== 'all' && row.status !== filterStatus) return false
    if (searchTerm && !row.skill.toLowerCase().includes(searchTerm.toLowerCase())) return false
    return true
  })

  const strong  = rows.filter(r => r.status === 'strong').length
  const partial = rows.filter(r => r.status === 'partial').length
  const missing = rows.filter(r => r.status === 'missing').length
  const overallPct = rows.length
    ? Math.round(rows.reduce((s, r) => s + r.score, 0) / rows.length)
    : 0

  const visible = showAll ? filteredRows : filteredRows.slice(0, 6)

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center gap-2">
        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
          <MinusCircle className="w-5 h-5 text-gray-400" />
        </div>
        <p className="text-sm font-medium text-gray-600">No skill data yet</p>
        <p className="text-xs text-gray-400">Apply to jobs to see how your skills compare</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-gray-800">Skill Match Breakdown</p>
            <p className="text-xs text-gray-400 mt-0.5">vs. {evaluations.length} jobs applied (real-time)</p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Updated: {lastUpdated}</span>
          <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-[11px]">Live</span>
        </div>
        {/* Overall score ring */}
        <div className="shrink-0 flex flex-col items-center">
          <div className={cn(
            'w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2',
            overallPct >= 70 ? 'border-green-400 text-green-700 bg-green-50' :
            overallPct >= 40 ? 'border-yellow-400 text-yellow-700 bg-yellow-50' :
                               'border-red-300 text-red-600 bg-red-50',
          )}>
            {overallPct}%
          </div>
          <p className="text-[10px] text-gray-400 mt-1">overall</p>
        </div>
      </div>

      {/* Summary pills */}
      <div className="flex gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1 text-xs bg-green-50 text-green-700 border border-green-200 px-2.5 py-1 rounded-full font-medium">
          <CheckCircle2 className="w-3 h-3" /> {strong} strong
        </span>
        <span className="inline-flex items-center gap-1 text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 px-2.5 py-1 rounded-full font-medium">
          <MinusCircle className="w-3 h-3" /> {partial} partial
        </span>
        <span className="inline-flex items-center gap-1 text-xs bg-red-50 text-red-600 border border-red-200 px-2.5 py-1 rounded-full font-medium">
          <XCircle className="w-3 h-3" /> {missing} missing
        </span>
      </div>

      {/* Filter controls */}
      <div className="flex gap-2 mb-3">
        <select 
          value={filterStatus} 
          onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
          className="text-xs border border-gray-200 rounded px-2.5 py-1 bg-white"
        >
          <option value="all">All ({rows.length})</option>
          <option value="strong">Strong ({strong})</option>
          <option value="partial">Partial ({partial})</option>
          <option value="missing">Missing ({missing})</option>
        </select>
        <input
          type="text"
          placeholder="Search skills..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 text-xs border border-gray-200 rounded px-2.5 py-1 bg-white"
        />
      </div>

      {/* Skill rows */}
      <div className="space-y-2.5">
        {visible.map(row => {
          const lbl = statusLabel(row.status)
          return (
            <div key={row.skill} className="group">
              <div className="flex items-center gap-2 mb-1">
                {statusIcon(row.status)}
                <span className="text-xs font-medium text-gray-800 flex-1 truncate">{row.skill}</span>
                <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded-full border shrink-0', lbl.cls)}>
                  {lbl.text}
                </span>
                <span className="text-xs font-bold text-gray-600 w-8 text-right shrink-0">
                  {row.score}%
                </span>
              </div>
              {/* Progress bar */}
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden ml-5">
                <div
                  className={cn('h-full rounded-full bg-gradient-to-r transition-all duration-500', barGradient(row.status))}
                  style={{ width: `${row.score}%` }}
                />
              </div>
              {/* Frequency hint — only on hover via group */}
              <p className="text-[10px] text-gray-400 ml-5 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                Required in {row.total} job{row.total !== 1 ? 's' : ''} · matched {row.matched}
              </p>
            </div>
          )
        })}
      </div>

      {/* Show more / less */}
      {rows.length > 6 && (
        <button
          onClick={() => setShowAll(s => !s)}
          className="w-full flex items-center justify-center gap-1.5 text-xs text-brand-600 hover:text-brand-800 font-medium py-1.5 border border-brand-100 rounded-lg hover:bg-brand-50 transition-colors"
        >
          {showAll
            ? <><ChevronUp className="w-3.5 h-3.5" /> Show less</>
            : <><ChevronDown className="w-3.5 h-3.5" /> Show {rows.length - 6} more skills</>}
        </button>
      )}
    </div>
  )
}
