import client from "./client"
import type { Recruiter } from "@/types/api"

export async function fetchRecruiters(): Promise<{
  recruiters: Recruiter[]
  total: number
  api_status: Record<string, boolean>
  warnings: string[]
}> {
  const { data } = await client.get("/api/recruiters")
  return data
}
