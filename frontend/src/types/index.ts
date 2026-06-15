// ─── Auth ────────────────────────────────────────────────────────────────────
export interface User {
  id: number
  email: string
  full_name: string
  role: 'candidate' | 'recruiter'  | 'superadmin'
  auth_provider: string
  created_at: string
  last_login_at: string | null
  candidate?: Candidate | null
  recruiter?: Recruiter | null
  
}

// ─── Candidate ───────────────────────────────────────────────────────────────
export interface Candidate {
  id: number
  user_id: number
  full_name: string
  email: string
  headline: string | null
  location: string | null
  summary: string | null
  years_experience: number | null
  skills: string[]
  links: string[]
  projects: Project[]
  neurodivergent?: boolean | null
  nd_type?: string | null
  github_username: string | null
  leetcode_username: string | null
  resume_url: string | null
  github_repos: number | null
  github_stars: number | null
  github_forks: number | null
  github_top_languages: string[]
  github_repos_data: GithubRepo[]
  lc_easy: number | null
  lc_medium: number | null
  lc_hard: number | null
  lc_rating: number | null
  resume_skills: string[]
  resume_projects: ResumeProject[]
  enrichment_status: 'none' | 'pending' | 'running' | 'done' | 'error'
  enrichment_error: string | null
  agent_statuses: Record<string, string>
  top_job_matches: JobMatch[]
  preferred_region: Region | null
  enriched_at: string | null
  created_at: string
  updated_at: string
}

export interface GithubRepo {
  name: string
  description: string
  language: string | null
  stars: number
  forks: number
  url: string
  updated_at: string
  topics: string[]
}

export interface ResumeProject {
  name: string
  description: string
}

export interface Project {
  name: string
  description: string
  url?: string
}

export interface JobMatch {
  id: number
  title: string
  company: string
  match_score: number
  url: string
  tags: string[]
}

// ─── Recruiter ───────────────────────────────────────────────────────────────
export interface Recruiter {
  id: number
  user_id: number
  full_name: string
  email: string
  company_name: string | null
  job_title: string | null
  created_at: string
  updated_at: string
}

// ─── Region ──────────────────────────────────────────────────────────────────
export interface Region {
  id: number
  name: string
  code: string
  is_active: boolean
}

// ─── Job ─────────────────────────────────────────────────────────────────────
export interface Job {
  id: number
  recruiter_id: number
  region: Region | null
  company: string
  company_name: string
  title: string
  location: string
  employment_type: string
  description: string
  requirements: string[]
  skills_required: string[]
  salary_min: number | null
  salary_max: number | null
  is_active: boolean
  application_count: number
  created_at: string
  updated_at: string
}

// ─── Application ─────────────────────────────────────────────────────────────
export interface Application {
  id: number
  job_id: number
  candidate_id: number
  status: 'applied' | 'in_review' | 'shortlisted' | 'rejected' | 'on_hold'
  cover_letter: string
  resume_url: string
  match_score: number | null
  confidence: string | null
  strengths: string[]
  gaps: string[]
  why_fit: string | null
  feedback_note: string | null
  is_shortlisted: boolean
  candidate?: Candidate
  job?: Job
  created_at: string
  updated_at: string
}

// ─── Evaluation ──────────────────────────────────────────────────────────────
export interface Evaluation {
  id: number
  candidate_id: number
  job_id: number
  score: number | null
  recommendation: 'YES' | 'NO' | 'MAYBE' | 'PENDING'
  strengths: string[]
  gaps: string[]
  why_fit: string | null
  nd_inclusion?: NDInclusionReport | null
  cultural_dna?: CulturalDNA | null
  eval_status: 'pending' | 'running' | 'done' | 'error'
  eval_error: string | null
  current_step?: string   // evidence | context | reasoning | ranking | feedback
  recruiter_action: 'pending' | 'shortlisted' | 'rejected'
  action_taken_at: string | null
  evaluated_at: string | null
  candidate?: Candidate
  job?: Job
  feedback_report?: FeedbackReport
  created_at: string
  updated_at: string
}

export interface CulturalDNADimension {
  dimension: string
  candidate_score: number
  company_score: number
  match_pct: number
  risk_note?: string | null
}

export interface CulturalDNA {
  overall_match_pct: number
  signal_type: string
  candidate_name: string
  company_name: string
  dimensions: CulturalDNADimension[]
}

export interface NDInclusionReport {
  nd_flag: boolean
  nd_type?: string | null
  nd_source?: 'self_declared' | 'inferred' | string
  risk_of_underestimation?: string | null
  recommended_action?: string | null
  penalty_reduction_weight?: number | null
  strengths_detected?: Array<{
    signal?: string
    trait_cluster?: string
    strength_label?: string
    evidence?: string
    weight?: string
  }>
  underestimation_risks?: Array<{
    risk_factor?: string
    description?: string
    affected_metric?: string
    severity?: string
  }>
}

// ─── Feedback ────────────────────────────────────────────────────────────────
export interface FeedbackReport {
  // Legacy flat fields (Backend/models.py FeedbackReport)
  candidate_report?: string
  recruiter_summary?: string
  interview_questions?: string[]
  fairness_assessment?: string
  generated_at: string | null
  generation_time_ms?: number
  // New learning path fields
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
}

// ─── Learning Hub ────────────────────────────────────────────────────────────
export interface LearningPath {
  evaluation_id: number
  job_title: string
  company: string
  generated_at: string
  learning_resources: FeedbackReport['learning_resources']
  task_checklist: FeedbackReport['task_checklist']
  completed_tasks: number
  total_tasks: number
}

// ─── Message ─────────────────────────────────────────────────────────────────
export interface Message {
  id: number
  sender_id: number
  recipient_id: number
  application_id: number | null
  subject: string
  body: string
  is_read: boolean
  is_mine: boolean
  sender_name: string | null
  recipient_name: string | null
  created_at: string
}

// ─── Notification ────────────────────────────────────────────────────────────
export interface Notification {
  id: number
  user_id: number
  type: string
  title: string
  body: string
  is_read: boolean
  link: string
  created_at: string
}

// ─── Scraped Job ─────────────────────────────────────────────────────────────
export interface ScrapedJob {
  id: number
  region: Region | null
  external_id: string
  title: string
  company: string
  location: string
  description: string
  tags: string[]
  url: string
  salary: string
  source: string
  posted_at: string | null
  scraped_at: string
  match_score?: number
}

// ─── Dashboard Candidate (recruiter view) ────────────────────────────────────
export interface DashboardCandidate {
  id: number
  user_id: number
  full_name: string
  email: string | null
  headline: string | null
  location: string | null
  years_experience: number | null
  skills: string[]
  resume_skills: string[]
  github_username: string | null
  github_repos: number | null
  github_stars: number | null
  lc_easy: number | null
  lc_medium: number | null
  lc_hard: number | null
  top_skill: string
  created_at: string
  latest_evaluation: {
    id: number
    job_id: number
    job_title: string
    job_company: string
    score: number | null
    recommendation: string
    recruiter_action: string
    strengths: string[]
    gaps: string[]
    why_fit: string | null
    evaluated_at: string | null
  } | null
}

// ─── Enrichment Status ───────────────────────────────────────────────────────
export interface EnrichmentStatus {
  enrichment_status: 'none' | 'pending' | 'running' | 'done' | 'partial' | 'error'
  enrichment_error: string | null
  enriched_at: string | null
  agent_statuses: Record<string, string>
  github_repos: number | null
  github_stars: number | null
  github_forks: number | null
  github_top_languages: string[]
  github_repos_data: GithubRepo[]
  lc_easy: number | null
  lc_medium: number | null
  lc_hard: number | null
  lc_rating: number | null
  resume_skills: string[]
  resume_projects: ResumeProject[]
  top_job_matches: JobMatch[]
}
