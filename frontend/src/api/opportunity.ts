import client from "./client"

export type OpportunitySignal = {
  level: string
  status: string
  confidence: number | null
  evidence: unknown[]
}

export type OpportunityIntelligence = {
  job_id: number | null
  competition_intensity: OpportunitySignal
  background_fit_sensitivity: OpportunitySignal
  shortlisting_strictness: OpportunitySignal
  determination_status: string
  evidence: unknown[]
  confidence: number | null
  computed_at: string | null
}

export async function fetchOpportunityIntelligence(jobId: number): Promise<OpportunityIntelligence> {
  const { data } = await client.get(`/api/jobs/${jobId}/opportunity-intelligence`)
  return data.opportunity_intelligence
}
