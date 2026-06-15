import { CheckCircle2, RefreshCw, Clock, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export type StepStatus = 'done' | 'running' | 'pending' | 'error' | 'skipped'

export interface AgentStep {
  id: string
  label: string
  description: string
  status: StepStatus
}

interface Props {
  steps: AgentStep[]
  compact?: boolean
}

const PIPELINE_STEPS: Omit<AgentStep, 'status'>[] = [
  { id: 'evidence',  label: 'GitHub analyzed',       description: 'Collecting repos, commits, LeetCode' },
  { id: 'context',   label: 'Skills matched',         description: 'Comparing your skills to job requirements' },
  { id: 'reasoning', label: 'AI reasoning complete',  description: 'Generating hiring recommendation' },
  { id: 'ranking',   label: 'Score computed',         description: 'Calculating composite ranking score' },
  { id: 'feedback',  label: 'Feedback generated',     description: 'Building your personalized report' },
]

/** Derive step statuses from eval_status + current_step */
export function deriveSteps(
  evalStatus: string,
  currentStep?: string,
): AgentStep[] {
  const stepIds = PIPELINE_STEPS.map(s => s.id)
  const currentIdx = currentStep ? stepIds.indexOf(currentStep) : -1

  return PIPELINE_STEPS.map((step, idx) => {
    let status: StepStatus = 'pending'

    if (evalStatus === 'done') {
      status = 'done'
    } else if (evalStatus === 'error') {
      // Steps before current are done, current is error, rest pending
      if (currentIdx >= 0) {
        if (idx < currentIdx) status = 'done'
        else if (idx === currentIdx) status = 'error'
        else status = 'pending'
      } else {
        status = 'error'
      }
    } else if (evalStatus === 'running' || evalStatus === 'pending') {
      if (currentIdx >= 0) {
        if (idx < currentIdx) status = 'done'
        else if (idx === currentIdx) status = 'running'
        else status = 'pending'
      } else {
        // No current_step info — show first as running
        status = idx === 0 ? 'running' : 'pending'
      }
    }

    return { ...step, status }
  })
}

function StepIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case 'done':    return <CheckCircle2 className="w-5 h-5 text-green-500" />
    case 'running': return <RefreshCw className="w-5 h-5 text-brand-500 animate-spin" />
    case 'error':   return <AlertCircle className="w-5 h-5 text-red-500" />
    default:        return <Clock className="w-5 h-5 text-gray-300" />
  }
}

export default function AgentStepper({ steps, compact = false }: Props) {
  if (!steps?.length) return null

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center gap-1">
            <div className={cn(
              'w-2 h-2 rounded-full',
              step.status === 'done'    ? 'bg-green-500' :
              step.status === 'running' ? 'bg-brand-500 animate-pulse' :
              step.status === 'error'   ? 'bg-red-500' :
                                          'bg-gray-200',
            )} />
            {i < steps.length - 1 && (
              <div className={cn(
                'w-4 h-0.5',
                step.status === 'done' ? 'bg-green-300' : 'bg-gray-200',
              )} />
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1
        return (
          <div key={step.id} className="flex gap-3">
            {/* Icon + connector */}
            <div className="flex flex-col items-center">
              <StepIcon status={step.status} />
              {!isLast && (
                <div className={cn(
                  'w-0.5 flex-1 mt-1 min-h-[20px]',
                  step.status === 'done' ? 'bg-green-200' : 'bg-gray-100',
                )} />
              )}
            </div>

            {/* Label */}
            <div className={cn('pb-4', isLast && 'pb-0')}>
              <p className={cn(
                'text-sm font-medium',
                step.status === 'done'    ? 'text-gray-900' :
                step.status === 'running' ? 'text-brand-700' :
                step.status === 'error'   ? 'text-red-600' :
                                            'text-gray-400',
              )}>
                {step.label}
              </p>
              {step.status === 'running' && (
                <p className="text-xs text-brand-600 mt-0.5">{step.description}</p>
              )}
              {step.status === 'error' && (
                <p className="text-xs text-red-500 mt-0.5">Failed — {step.description}</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
