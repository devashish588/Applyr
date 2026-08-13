import client from "./client"
import type { PipelineConfig, SetupStatus, Profile } from "@/types/api"

export async function fetchConfig(): Promise<PipelineConfig> {
  const { data } = await client.get("/api/config")
  return data
}

export async function fetchSetupStatus(): Promise<SetupStatus> {
  const { data } = await client.get("/api/setup/status")
  return data
}

export async function fetchProfile(): Promise<Profile> {
  const { data } = await client.get("/api/profile")
  return data.profile
}

export async function updateProfile(updates: Partial<Profile>): Promise<Profile> {
  const { data } = await client.put("/api/profile", updates)
  return data.profile
}

export async function fetchGmailAuthUrl(): Promise<string> {
  const { data } = await client.get("/api/gmail/auth-url")
  return data.auth_url
}

export async function fetchGmailStatus(): Promise<Record<string, unknown>> {
  const { data } = await client.get("/api/gmail/status")
  return data
}

export async function disconnectGmail(): Promise<void> {
  await client.post("/api/gmail/disconnect")
}

export async function fetchSearchStrategy(): Promise<Record<string, unknown>> {
  const { data } = await client.get("/api/search-strategy")
  return data.strategy || {}
}
