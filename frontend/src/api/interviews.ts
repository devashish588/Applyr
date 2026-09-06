import client from "./client"

export async function fetchInterviews(appId: number) {
  const { data } = await client.get(`/api/applications/${appId}/interviews`)
  return data.interviews || []
}
export async function createInterview(appId: number, payload: any) {
  const { data } = await client.post(`/api/applications/${appId}/interviews`, payload)
  return data.interview
}
export async function completeInterview(interviewId: number, notes?: string) {
  const { data } = await client.post(`/api/interviews/${interviewId}/complete`, { notes })
  return data.interview
}
export async function fetchInterviewPrep(appId: number) {
  const { data } = await client.get(`/api/applications/${appId}/interview-prep`)
  return data.prep
}
export async function fetchFollowUps(appId: number) {
  const { data } = await client.get(`/api/applications/${appId}/follow-ups`)
  return data.follow_ups || []
}
export async function createFollowUp(appId: number, payload: any) {
  const { data } = await client.post(`/api/applications/${appId}/follow-ups`, payload)
  return data.follow_up
}
export async function reviewFollowUp(id: number) {
  const { data } = await client.post(`/api/follow-ups/${id}/review`)
  return data.follow_up
}
export async function approveFollowUp(id: number) {
  const { data } = await client.post(`/api/follow-ups/${id}/approve`)
  return data.follow_up
}
export async function sendFollowUp(id: number) {
  const { data } = await client.post(`/api/follow-ups/${id}/send`)
  return data.follow_up
}
export async function cancelInterview(interviewId: number) {
  const { data } = await client.post(`/api/interviews/${interviewId}/cancel`)
  return data.interview || data
}
