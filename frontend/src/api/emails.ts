import client from "./client"
import type { EmailDraft } from "@/types/api"

export async function fetchEmailDrafts(): Promise<EmailDraft[]> {
  const { data } = await client.get("/api/emails")
  return data.emails || []
}

export async function sendEmails(items: { id: number; subject?: string; body?: string }[]): Promise<{
  sent: number
  failed: { id: number; company?: string; reason: string }[]
  total: number
}> {
  const { data } = await client.post("/api/emails/send", { items })
  return data
}

export async function sendTestEmail(to?: string): Promise<Record<string, unknown>> {
  const { data } = await client.post("/api/email/test", to ? { to } : {})
  return data
}

export async function fetchEmailDiagnostics(): Promise<Record<string, unknown>> {
  const { data } = await client.get("/api/email-status")
  return data
}
