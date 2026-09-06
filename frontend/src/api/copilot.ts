import client from "./client"
import type { CopilotRequest, CopilotResponse } from "@/types/api"

export async function askCopilot(payload: CopilotRequest): Promise<CopilotResponse> {
  const { data } = await client.post<CopilotResponse>("/api/copilot/chat", payload)
  return data
}
