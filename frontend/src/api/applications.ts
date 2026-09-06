import client from "./client"

export async function fetchApplications(): Promise<any[]> {
  const { data } = await client.get("/api/applications")
  return data.applications || []
}

export async function createApplication(jobId: number): Promise<any> {
  const { data } = await client.post("/api/applications", { job_id: jobId })
  return data.application
}

export async function fetchApplication(appId: number): Promise<any> {
  const { data } = await client.get(`/api/applications/${appId}`)
  return data.application || data
}

export async function updateApplicationState(appId: number, state: string): Promise<any> {
  const { data } = await client.patch(`/api/applications/${appId}`, { state })
  return data.application
}

export async function applyApplication(appId: number): Promise<any> {
  const { data } = await client.post(`/api/applications/${appId}/apply`)
  return data.application
}

export async function postOutcome(appId: number, outcome: string, reason?: string): Promise<any> {
  const { data } = await client.post(`/api/applications/${appId}/outcome`, { outcome, reason })
  return data.application
}

export async function postApplicationEvent(appId: number, event_type: string, payload?: any): Promise<any> {
  const { data } = await client.post(`/api/applications/${appId}/events`, { event_type, payload })
  return data.event
}

export async function fetchApplicationTimeline(appId: number): Promise<any[]> {
  const { data } = await client.get(`/api/applications/${appId}/timeline`)
  return data.timeline || []
}
