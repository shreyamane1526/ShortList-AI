// ─── Agent 5 Feedback Types ───────────────────────────────────────────────────

export interface WhyNotSelected {
  reasons: string[]
  tone: string
  improvement_hints: string[]
}

export interface ImprovementPlan {
  short_term: string[]
  long_term: string[]
}

export interface LearningWeek {
  week: number
  topic: string
  resources: string[]
}

export interface SkillMatchVisualization {
  required_skills: string[]
  matched: string[]
  missing: string[]
  partial: string[]
}

export interface ConfidenceScore {
  score: number
  level: 'Low' | 'Medium' | 'High'
  factors: string[]
}

export interface RichFeedbackReport {
  why_not_selected: WhyNotSelected
  improvement_plan: ImprovementPlan
  learning_path: LearningWeek[]
  skill_match_visualization: SkillMatchVisualization
  confidence_score: ConfidenceScore
  badges: string[]
  candidate_report_markdown: string
  recruiter_summary: string
  nd_inclusion?: {
    nd_flag: boolean
    nd_type?: string | null
    nd_source?: 'self_declared' | 'inferred' | string
  } | null
  // New adaptive learning path fields
  learning_resources?: {
    weekly_plan?: Array<{
      week: number
      focus: string
      goals: string[]
      estimated_hours: number
    }>
    resources?: Array<{
      title: string
      type: string
      url: string
      description: string
      duration?: string
    }>
    market_trends?: string[]
  }
  task_checklist?: Array<{
    id: string
    task: string
    completed: boolean
    week: number
    resource_url?: string
    type: string
  }>
  _meta?: {
    evaluation_id: string
    generated_at: string
    generation_time_ms: number | null
  }
}

// Pipeline evaluation step names
export type PipelineStep = 'evidence' | 'context' | 'reasoning' | 'ranking' | 'feedback'
