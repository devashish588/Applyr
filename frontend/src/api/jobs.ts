import client from "./client"
import type { Job, MatchDetails } from "@/types/api"

export async function fetchJobs(): Promise<Job[]> {
  const { data } = await client.get("/api/jobs")
  return data.jobs || []
}

export async function fetchJobDetail(jobId: number): Promise<{ job: Job; match: MatchDetails | null }> {
  const { data } = await client.get(`/api/jobs/${jobId}`)
  return { job: data.job, match: data.match || null }
}

export async function fetchJobMatch(jobId: number): Promise<MatchDetails> {
  const { data } = await client.get(`/api/jobs/${jobId}/match`)
  return data.match
}

export async function updateJobCompany(jobId: number, company: string): Promise<void> {
  await client.post(`/api/jobs/${jobId}/company`, { company })
}

export async function fetchPrioritizedJobs(): Promise<any[]> {
  const { data } = await client.get("/api/jobs/prioritized")
  return data.jobs || []
}

export async function fetchJobPriority(jobId: number): Promise<any> {
  const { data } = await client.get(`/api/jobs/${jobId}/priority`)
  return data.priority
}
