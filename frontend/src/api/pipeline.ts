import client from "./client"

export async function runPipeline(): Promise<{ run_id: string }> {
  const { data } = await client.post("/api/run-now")
  return data
}

export async function uploadJD(file: File): Promise<{ run_id: string; filename: string }> {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await client.post("/api/upload-jd", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return data
}

export async function pasteJD(jdText: string): Promise<{ run_id: string }> {
  const { data } = await client.post("/api/paste-jd", { jd_text: jdText })
  return data
}

export async function fetchPipelineLogs(runId: string): Promise<Record<string, unknown>[]> {
  const { data } = await client.get(`/api/pipeline/logs/${runId}`)
  return data.events || []
}

export async function fetchRunLogs(): Promise<Record<string, unknown>[]> {
  const { data } = await client.get("/api/logs")
  return data.runs || []
}

export function createPipelineStream(runId: string): EventSource {
  return new EventSource(`/api/pipeline/stream/${runId}`)
}
