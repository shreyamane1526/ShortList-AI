import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { format, subDays, startOfDay } from 'date-fns'
import type { Evaluation } from '@/types'

// ── Skeleton ──────────────────────────────────────────────────────────────────
function Skeleton({ h = 'h-32' }: { h?: string }) {
  return <div className={`animate-pulse bg-gray-100 rounded-lg ${h}`} />
}

// ── Evaluation trend (area chart) ─────────────────────────────────────────────
interface TrendProps { evaluations: Evaluation[]; loading?: boolean }

export function EvalTrendChart({ evaluations, loading }: TrendProps) {
  if (loading) return <Skeleton h="h-28" />

  const today = startOfDay(new Date())
  const data = Array.from({ length: 7 }, (_, i) => {
    const day = subDays(today, 6 - i)
    const label = format(day, 'MMM d')
    const count = evaluations.filter(ev =>
      startOfDay(new Date(ev.created_at)).getTime() === day.getTime()
    ).length
    return { label, count }
  })

  return (
    <ResponsiveContainer width="100%" height={110}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
        <defs>
          <linearGradient id="evalGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
        <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          formatter={(v: number) => [v, 'Evaluations']}
        />
        <Area type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2}
          fill="url(#evalGrad)" dot={{ r: 3, fill: '#3b82f6' }} activeDot={{ r: 5 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ── Pipeline donut chart ──────────────────────────────────────────────────────
interface DonutProps { evaluations: Evaluation[]; loading?: boolean }

const DONUT_COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#6b7280']

export function PipelineDonut({ evaluations, loading }: DonutProps) {
  if (loading) return <Skeleton h="h-28" />

  const shortlisted = evaluations.filter(e => e.recruiter_action === 'shortlisted').length
  const rejected    = evaluations.filter(e => e.recruiter_action === 'rejected').length
  const pending     = evaluations.filter(e => e.recruiter_action === 'pending' && e.eval_status === 'done').length
  const running     = evaluations.filter(e => e.eval_status === 'pending' || e.eval_status === 'running').length

  const data = [
    { name: 'Shortlisted', value: shortlisted },
    { name: 'Rejected',    value: rejected },
    { name: 'Pending',     value: pending },
    { name: 'Evaluating',  value: running },
  ].filter(d => d.value > 0)

  if (data.length === 0) {
    return (
      <div className="h-28 flex items-center justify-center text-xs text-gray-400">
        No evaluations yet
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={110}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={28}
          outerRadius={44}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ fontSize: 11, borderRadius: 8, border: '1px solid #e5e7eb' }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 10 }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
