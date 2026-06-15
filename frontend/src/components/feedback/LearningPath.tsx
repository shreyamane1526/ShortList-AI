import { useState } from 'react'
import { BookOpen, CheckSquare, Square, ExternalLink, ChevronDown, ChevronUp, Clock, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import type { FeedbackReport } from '@/types'
import type { LearningWeek } from '@/types/feedback'

interface Props {
  weeks?: LearningWeek[]
  learningResources?: FeedbackReport['learning_resources']
  taskChecklist?: FeedbackReport['task_checklist']
}

export default function LearningPath({ weeks, learningResources, taskChecklist }: Props) {
  const [checkedTasks, setCheckedTasks] = useState<Set<string>>(new Set(
    taskChecklist?.filter(t => t.completed).map(t => t.id) || []
  ))
  const [open, setOpen] = useState(true)
  const [updating, setUpdating] = useState<string | null>(null)

  const isLegacyPath = !!weeks?.length && !learningResources?.weekly_plan?.length
  const hasNewPath = !!learningResources?.weekly_plan?.length || !!taskChecklist?.length

  if (!isLegacyPath && !hasNewPath) return null

  async function toggleTask(taskId: string) {
    setUpdating(taskId)
    try {
      const res = await api.patch(`/learning/check/${taskId}`)
      const task = res.data.task
      setCheckedTasks(prev => {
        const next = new Set(prev)
        task.completed ? next.add(taskId) : next.delete(taskId)
        return next
      })
      toast.success(task.completed ? 'Task completed!' : 'Task unchecked')
    } catch (err: any) {
      toast.error('Failed to update task')
    } finally {
      setUpdating(null)
    }
  }

  function toggleLegacyWeek(weekId: string) {
    setCheckedTasks(prev => {
      const next = new Set(prev)
      next.has(weekId) ? next.delete(weekId) : next.add(weekId)
      return next
    })
  }

  const completedTasks = checkedTasks.size
  const totalTasks = taskChecklist?.length || 0
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0

  if (isLegacyPath && weeks) {
    const completedWeeks = weeks.filter(w => checkedTasks.has(`week-${w.week}`)).length
    return (
      <div className="rounded-xl border border-brand-200 bg-brand-50 overflow-hidden">
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-brand-100/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
              <BookOpen className="w-4 h-4 text-brand-600" />
            </div>
            <div>
              <p className="font-semibold text-brand-900 text-sm">AI Learning Path</p>
              <p className="text-xs text-brand-700 mt-0.5">
                {completedWeeks}/{weeks.length} weeks completed
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1">
              {weeks.map(w => (
                <div
                  key={w.week}
                  className={cn(
                    'w-2 h-2 rounded-full transition-colors',
                    checkedTasks.has(`week-${w.week}`) ? 'bg-brand-600' : 'bg-brand-200',
                  )}
                />
              ))}
            </div>
            {open
              ? <ChevronUp className="w-4 h-4 text-brand-500 shrink-0" />
              : <ChevronDown className="w-4 h-4 text-brand-500 shrink-0" />}
          </div>
        </button>

        {open && (
          <div className="px-5 pb-5 space-y-3">
            {weeks.map((week, idx) => {
              const weekKey = `week-${week.week}`
              const done = checkedTasks.has(weekKey)
              const isLast = idx === weeks.length - 1

              return (
                <div key={week.week} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <button
                      onClick={() => toggleLegacyWeek(`week-${week.week}`)}
                      className="mt-0.5 shrink-0 text-brand-600 hover:text-brand-800 transition-colors"
                      aria-label={done ? 'Mark incomplete' : 'Mark complete'}
                    >
                      {done
                        ? <CheckSquare className="w-5 h-5" />
                        : <Square className="w-5 h-5 text-brand-300" />}
                    </button>
                    {!isLast && (
                      <div className={cn(
                        'w-0.5 flex-1 mt-1 min-h-[24px]',
                        done ? 'bg-brand-400' : 'bg-brand-200',
                      )} />
                    )}
                  </div>

                  <div className={cn(
                    'flex-1 bg-white rounded-xl border p-4 transition-all',
                    done ? 'border-brand-300 opacity-60' : 'border-brand-100',
                  )}>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-xs font-bold text-brand-600 uppercase tracking-wide">
                          Week {week.week}
                        </span>
                        <p className={cn(
                          'font-semibold text-sm mt-0.5',
                          done ? 'line-through text-gray-400' : 'text-gray-900',
                        )}>
                          {week.topic}
                        </p>
                      </div>
                      {done && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full shrink-0">
                          Done ✓
                        </span>
                      )}
                    </div>

                    {week.resources?.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {week.resources.map((res, ri) => {
                          const isUrl = res.startsWith('http')
                          return isUrl ? (
                            <a
                              key={ri}
                              href={res}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-800 bg-brand-50 border border-brand-100 px-2 py-0.5 rounded-full hover:bg-brand-100 transition-colors"
                            >
                              <ExternalLink className="w-3 h-3" />
                              {res.replace(/^https?:\/\//, '').split('/')[0]}
                            </a>
                          ) : (
                            <span
                              key={ri}
                              className="inline-flex items-center gap-1 text-xs text-gray-600 bg-gray-50 border border-gray-100 px-2 py-0.5 rounded-full"
                            >
                              📚 {res}
                            </span>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  const marketTrends = learningResources?.market_trends ?? []
  const resources = learningResources?.resources ?? []

  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-brand-100/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
            <BookOpen className="w-4 h-4 text-brand-600" />
          </div>
          <div>
            <p className="font-semibold text-brand-900 text-sm">AI Learning Path</p>
            <p className="text-xs text-brand-700 mt-0.5">
              {completedTasks}/{totalTasks} tasks completed ({progressPercent}%)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Progress bar */}
          <div className="hidden sm:block w-16 h-2 bg-brand-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {open
            ? <ChevronUp className="w-4 h-4 text-brand-500 shrink-0" />
            : <ChevronDown className="w-4 h-4 text-brand-500 shrink-0" />}
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4">
          {/* Market Trends */}
          {marketTrends.length > 0 && (
            <div className="bg-white rounded-lg border border-brand-100 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-brand-600" />
                <p className="text-sm font-semibold text-brand-900">Market Trends</p>
              </div>
              <ul className="space-y-1">
                {marketTrends.map((trend, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-brand-500 mt-0.5">•</span>
                    {trend}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Weekly Plan */}
          {learningResources?.weekly_plan?.map((week) => (
            <div key={week.week} className="bg-white rounded-lg border border-brand-100 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-brand-600" />
                <span className="text-sm font-semibold text-brand-900">Week {week.week}</span>
                <span className="text-xs text-gray-500">({week.estimated_hours}h)</span>
              </div>
              <p className="text-sm font-medium text-gray-900 mb-2">{week.focus}</p>
              <ul className="space-y-1 mb-3">
                {week.goals.map((goal, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-brand-500 mt-0.5">•</span>
                    {goal}
                  </li>
                ))}
              </ul>
              {/* Tasks for this week */}
              {taskChecklist?.filter(t => t.week === week.week).map((task) => (
                <div key={task.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <button
                    onClick={() => toggleTask(task.id)}
                    disabled={updating === task.id}
                    className="mt-0.5 text-brand-600 hover:text-brand-800 transition-colors disabled:opacity-50"
                  >
                    {updating === task.id ? (
                      <div className="w-5 h-5 border-2 border-brand-300 border-t-brand-600 rounded-full animate-spin" />
                    ) : checkedTasks.has(task.id) ? (
                      <CheckSquare className="w-5 h-5" />
                    ) : (
                      <Square className="w-5 h-5 text-brand-300" />
                    )}
                  </button>
                  <div className="flex-1">
                    <p className={cn(
                      'text-sm',
                      checkedTasks.has(task.id) ? 'line-through text-gray-500' : 'text-gray-900'
                    )}>
                      {task.task}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                        {task.type}
                      </span>
                      {task.resource_url && (
                        <a
                          href={task.resource_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-brand-600 hover:text-brand-800 flex items-center gap-1"
                        >
                          <ExternalLink className="w-3 h-3" />
                          Resource
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}

          {/* Resources */}
          {resources.length > 0 && (
            <div className="bg-white rounded-lg border border-brand-100 p-4">
              <p className="text-sm font-semibold text-brand-900 mb-3">Recommended Resources</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {resources.map((res, i) => (
                  <a
                    key={i}
                    href={res.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-3 border border-gray-200 rounded-lg hover:border-brand-300 hover:bg-brand-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{res.title}</p>
                        <p className="text-xs text-gray-600 mt-1">{res.description}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                            {res.type}
                          </span>
                          {res.duration && (
                            <span className="text-xs text-gray-500">{res.duration}</span>
                          )}
                        </div>
                      </div>
                      <ExternalLink className="w-4 h-4 text-gray-400 shrink-0" />
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
