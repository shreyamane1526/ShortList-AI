import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { format, subDays, startOfDay } from 'date-fns'
import type { Evaluation } from '@/types'

interface Props {
  evaluations: Evaluation[]
  loading?: boolean
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-2 pt-2">
      <div className="h-3 bg-gray-200 rounded w-1/3" />
      <div className="h-32 bg-gray-100 rounded-lg" />
    </div>
  )
}

export default function ApplicationTrendChart({ evaluations, loading }: Props) {
  if (loading) return <Skeleton />

  // Build last-7-days buckets from real evaluation created_at timestamps
  const today = startOfDay(new Date())
  const data = Array.from({ length: 7 }, (_, i) => {
    const day = subDays(today, 6 - i)
    const label = format(day, 'MMM d')
    const count = evaluations.filter(ev => {
      const d = startOfDay(new Date(ev.created_at))
      return d.getTime() === day.getTime()
    }).length
    return { label, count }
  })

  const hasData = data.some(d => d.count > 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-gray-700">Application Activity</p>
        <span className="text-xs text-gray-400">Last 7 days</span>
      </div>
      {!hasData ? (
        <div className="h-32 flex items-center justify-center text-sm text-gray-400">
          No applications in the last 7 days
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart data={data} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
              formatter={(v: number) => [v, 'Applications']}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#areaGrad)"
              dot={{ r: 3, fill: '#3b82f6' }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
