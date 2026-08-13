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
