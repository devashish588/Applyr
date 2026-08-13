export interface ApiResponse<T = unknown> {
  success?: boolean
  error?: string
  [key: string]: unknown
  data?: T
}

export interface Job {
  id: number
  title: string | null
  company: string | null
  url: string | null
  source: string | null
  location: string | null
  type: string | null
  hr_email: string | null
  jd_text: string | null
  fit_score: number | null
  status: string | null
  scraped_at: string | null
  applied_at: string | null
  cover_letter_path: string | null
  tailored_resume_path: string | null
  email_subject: string | null
  email_body: string | null
  match_details_json: string | null
  needs_review: number | null
  required_skills?: string[]
}

export interface MatchDetails {
  final_score: number
  recommendation: string
  explanation: string
  why_this_score?: string
  skill_match?: MatchComponent
  experience_match?: MatchComponent
  role_match?: MatchComponent
  location_match?: MatchComponent
  seniority_match?: MatchComponent
  matched_skills?: string[]
  missing_skills?: string[]
  matched_requirements?: string[]
  missing_requirements?: string[]
  skills_to_highlight?: string[]
}

export interface MatchComponent {
  score: number
  max_score: number
  weight: number
  weighted_score: number
  label: string
  details: string[]
  matched: string[]
  missing: string[]
}

export interface Recruiter {
  id: number
  company: string | null
  job_id: number | null
  name: string | null
  role: string | null
  department: string | null
  email: string | null
  confidence: number
  source: string | null
  linkedin: string | null
  contact_type: string | null
  rank_score: number
  discovered_at: string | null
}

export interface ResumeStatus {
  uploaded: boolean
  parsed: ResumeParseInfo | false
  path?: string
  filename?: string
  size?: number
  modified?: string
}

export interface ResumeParseInfo {
  name: string
  email: string
  confidence: number
  quality_score: number
  skills_count: number
  experience_count: number
  education_count: number
}

export interface ParsedResume {
  success: boolean
  filename?: string
  file_size?: number
  uploaded_at?: string
  parse_status?: string
  parsed_json?: Record<string, unknown>
  skills_json?: string[] | Record<string, string[]>
  roles_json?: string[] | ScoredRole[]
  error?: string
}

export interface ScoredRole {
  role: string
  score: number
}

export interface Analytics {
  total_jobs: number
  strong_matches: number
  recruiters_found: number
  applications_drafted: number
  applications_submitted: number
  responses: number
  interviews: number
  offers: number
  emails_drafted: number
  emails_sent: number
  avg_score: number
  total_runs: number
  source_distribution: Record<string, number>
  startup_matches: number
  referral_opportunities: number
  followups_due: number
  interviews_scheduled: number
  offers_received: number
  applications_by_source: Record<string, number>
  application_status_breakdown: Record<string, number>
  referral_success_rate: number
  interview_conversion_rate: number
  company_response_rate: number
  dry_run: boolean
}

export interface SystemStatus {
  status: string
  timestamp: string
  resume_uploaded: boolean
  resume_parsed: boolean
  resume_path: string | null
  recruiters_count: number
  env_keys: Record<string, boolean>
  email: {
    configured: boolean
    from_email: string | null
    provider: string | null
    gmail_status?: string
    health?: string
  }
  recruiter_discovery: {
    apollo?: boolean
    hunter: boolean
    clearbit: boolean
    active: boolean
  }
}

export interface EmailStatus {
  success: boolean
  configured: boolean
  provider: string | null
  from_email: string | null
  resend_configured: boolean
  gmail: {
    configured: boolean
    account: string | null
    status: string
    has_credentials: boolean
    has_token: boolean
    token_expired: boolean
  }
}

export interface PipelineConfig {
  dry_run: boolean
  auto_apply: boolean
  min_fit_score: number
  max_emails_per_run: number
  max_per_day: number
  scheduler_enabled: boolean
  scheduler_cron: string
}

export interface PipelineEvent {
  step: string
  msg: string
  pct: number
  agent: string
  status: string
  timestamp?: string
  count?: number
  results?: Record<string, unknown>
  error?: string
  blocked?: boolean
  validation?: Record<string, unknown>
  duration_ms?: number
}

export interface SetupStep {
  id: string
  label: string
  ok: boolean
  message: string
}

export interface SetupStatus {
  success: boolean
  steps: SetupStep[]
  completed: number
  total: number
  percent: number
  ready: boolean
}

export interface EmailDraft {
  id: number
  title: string | null
  company: string | null
  hr_email: string | null
  email_subject: string | null
  email_body: string | null
  status: string | null
  fit_score: number | null
}

export interface Profile {
  personal: {
    name: string
    email: string
    phone: string
    linkedin: string
    github: string
    portfolio: string
    city: string
    pincode: string
  }
  skills: Record<string, string[]>
  job_preferences: {
    target_roles: string[]
    target_locations: string[]
    min_salary: number
    remote_ok: boolean
    fulltime_only: boolean
    interested_industries: string[]
  }
  experience_summary: string
  key_achievements: string[]
  inferred_roles?: string[]
}

export interface RunLog {
  id: number
  run_id: string
  triggered_by: string | null
  started_at: string | null
  finished_at: string | null
  jobs_found: number
  jobs_filtered: number
  jobs_applied: number
  emails_sent: number
  errors_count: number
  status: string
  summary_json: string | null
}
