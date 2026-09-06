import client from "./client"
import type { Analytics, SystemStatus, EmailStatus } from "@/types/api"

export async function fetchAnalytics(): Promise<Analytics> {
  const { data } = await client.get("/api/analytics")
  return data.analytics
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const { data } = await client.get("/api/status")
  return data
}

export async function fetchEmailStatus(): Promise<EmailStatus> {
  const { data } = await client.get("/api/email/status")
  return data
}

export interface FunnelData {
  applications_started: number
  applications_submitted: number
  screening_count: number
  interview_count: number
  final_count: number
  offer_count: number
  accepted_count: number
  rejected_count: number
  application_to_screening_rate: number | null
  application_to_interview_rate: number | null
  interview_to_final_rate: number | null
  final_to_offer_rate: number | null
  offer_to_acceptance_rate: number | null
  application_to_offer_rate: number | null
}

export interface SourcePerf {
  source: string
  applications: number
  interviews: number
  offers: number
  accepted: number
  rejected: number
  interview_rate: number | null
  offer_rate: number | null
  status: string
}

export interface PriorityInsight {
  tier: string
  applications: number
  interviews: number
  offers: number
  interview_rate: number | null
  offer_rate: number | null
  status: string
}

export interface InsightsResponse {
  status: string
  sample_size: number
  insights: Array<{
    dimension: string
    segment: string
    applications: number
    interviews: number
    offers: number
    interview_rate: number | null
    confidence: string
  }>
}

export async function fetchOutcomeOverview(): Promise<{ funnel: FunnelData; time: Record<string, number | null> }> {
  const { data } = await client.get("/api/analytics/overview")
  return data
}

export async function fetchOutcomeSources(): Promise<SourcePerf[]> {
  const { data } = await client.get("/api/analytics/sources")
  return data.sources
}

export async function fetchOutcomeInsights(): Promise<InsightsResponse> {
  const { data } = await client.get("/api/analytics/insights")
  return data.insights
}
