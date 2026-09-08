/**
 * Single source of truth for next-action mapping.
 * Used by Job Details, Application Detail, Opportunities, Dashboard.
 * Do not duplicate this mapping elsewhere.
 */
export type NextAction = {
  label: string
  to: string
  variant: "primary" | "secondary" | "ghost"
  description: string
  disabled?: boolean
}

const BASE: Record<string, { label: string; description: string }> = {
  DISCOVERED: { label: "Review match", description: "Check fit and priority" },
  PREPARING: { label: "Open Application Studio", description: "Tailor resume & cover" },
  READY_TO_APPLY: { label: "Review & Apply", description: "Final review before apply" },
  APPLIED: { label: "Track application", description: "Monitor status" },
  SCREENING: { label: "Prepare for interview", description: "Screening prep" },
  INTERVIEW: { label: "Prepare for interview", description: "Interview prep & follow-up" },
  FINAL: { label: "Prepare for final stage", description: "Final round prep" },
  OFFER: { label: "Review offer", description: "Record outcome" },
  CLOSED: { label: "View outcome", description: "See outcome & learn" },
}

export function getNextActionForApplication(app: {
  id: number
  job_id: number
  current_state: string
  final_outcome?: string | null
}): NextAction {
  const state = app.current_state || "PREPARING"
  const base = BASE[state] || BASE.CLOSED
  const toMap: Record<string, string> = {
    DISCOVERED: `/jobs/${app.job_id}`,
    PREPARING: `/studio/${app.job_id}`,
    READY_TO_APPLY: `/applications/${app.id}`,
    APPLIED: `/applications/${app.id}`,
    SCREENING: `/applications/${app.id}?tab=interview`,
    INTERVIEW: `/applications/${app.id}?tab=interview`,
    FINAL: `/applications/${app.id}?tab=interview`,
    OFFER: `/applications/${app.id}?tab=outcome`,
    CLOSED: `/applications/${app.id}?tab=outcome`,
  }
  return {
    label: base.label,
    description: base.description,
    to: toMap[state] || `/applications/${app.id}`,
    variant: state === "OFFER" || state === "READY_TO_APPLY" ? "primary" : state === "CLOSED" ? "ghost" : "secondary",
  }
}

export function getNextActionForJob(job: { id: number }, application?: { id: number; current_state: string } | null): NextAction {
  if (!application) {
    return {
      label: BASE.DISCOVERED.label,
      description: BASE.DISCOVERED.description,
      to: `/jobs/${job.id}`,
      variant: "primary",
    }
  }
  return getNextActionForApplication(application as any)
}

export function getNextActionLabel(state: string): string {
  return BASE[state]?.label || "View details"
}
