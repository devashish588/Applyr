import client from "./client"

export async function fetchTracker(): Promise<any[]> {
  const { data } = await client.get("/api/tracker")
  return data.applications || []
}

export async function fetchFollowupsDue(): Promise<any[]> {
  const { data } = await client.get("/api/tracker/followups")
  return data.applications || []
}
