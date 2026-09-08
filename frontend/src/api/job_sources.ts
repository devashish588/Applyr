import client from "./client"

export type JobSource = {
  id: string
  name: string
  url: string
  host: string
  enabled: boolean
  source_type: string
  adapter: string
  created_at: string
  updated_at: string
  last_run_at?: string | null
  last_success_at?: string | null
  last_failure_at?: string | null
  last_job_count: number
  last_duration_ms: number
  failure_category?: string | null
  last_error?: string | null
}

export async function fetchJobSources(): Promise<{ sources: JobSource[]; total: number }> {
  const { data } = await client.get("/api/job-sources")
  return data
}

export async function createJobSource(payload: { url: string; name?: string; enabled?: boolean; source_type?: string }) {
  const { data } = await client.post("/api/job-sources", payload)
  return data.source as JobSource
}

export async function updateJobSource(id: string, payload: Partial<JobSource>) {
  const { data } = await client.put(`/api/job-sources/${id}`, payload)
  return data.source as JobSource
}

export async function deleteJobSource(id: string) {
  const { data } = await client.delete(`/api/job-sources/${id}`)
  return data
}

export async function testJobSource(id: string) {
  const { data } = await client.post(`/api/job-sources/${id}/test`)
  return data.result as { source_id: string; status: string; adapter: string; jobs_found: number; failure_category: string; error?: string; duration_ms: number; sample: any[] }
}

export async function fetchJobSourcesHealth() {
  const { data } = await client.get("/api/job-sources/health")
  return data as { success: boolean; configured: number; enabled: number; sources: any[]; recent_runs: any[] }
}

export async function fetchJobSourcesForJob(jobId: number) {
  const { data } = await client.get(`/api/jobs/${jobId}/sources`)
  return data as { success: boolean; job_id: number; sources: { source_id: string; name: string; host: string; mode: string; adapter: string; url: string; first_seen: string; last_seen: string }[]; primary: any; count: number }
}

export async function fetchDiversity() {
  const { data } = await client.get("/api/sources/diversity")
  return data as { success: boolean; total_canonical: number; diversity: { source: string; count: number; pct: number }[]; concentration_warning: string | null; new_jobs_last_run: number }
}

export async function fetchDiagnostics() {
  const { data } = await client.get("/api/sources/diagnostics")
  return data as { success: boolean; diagnostics: any[] }
}
