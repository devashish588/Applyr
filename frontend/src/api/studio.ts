import client from "./client"

export async function fetchStudio(jobId: number): Promise<any> {
  const { data } = await client.get(`/api/applications/studio/${jobId}`)
  return data.studio
}

export async function generateStudio(jobId: number): Promise<any> {
  const { data } = await client.post(`/api/applications/studio/${jobId}`, {}, { timeout: 60000 })
  return data.studio
}
