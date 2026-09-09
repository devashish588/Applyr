import client from "./client"
import type { ResumeStatus, ParsedResume } from "@/types/api"

export async function fetchResumeStatus(): Promise<ResumeStatus> {
  const { data } = await client.get("/api/resume-status")
  return data
}

export async function fetchParsedResume(): Promise<ParsedResume> {
  const { data } = await client.get("/api/resume/parsed")
  return data
}

export async function fetchResumeSkills(): Promise<string[]> {
  const { data } = await client.get("/api/resume/skills")
  return data.skills || []
}

export async function fetchResumeRoles(): Promise<unknown[]> {
  const { data } = await client.get("/api/resume/roles")
  return data.roles || []
}

export async function fetchResumeExperience(): Promise<Record<string, unknown>[]> {
  const { data } = await client.get("/api/resume/experience")
  return data.experience || []
}

export async function fetchResumeEducation(): Promise<Record<string, unknown>[]> {
  const { data } = await client.get("/api/resume/education")
  return data.education || []
}

export async function fetchResumeHealth(): Promise<Record<string, boolean>> {
  const { data } = await client.get("/api/resume/health")
  return data.health || {}
}

export async function uploadResume(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await client.post("/api/upload-resume", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  })
  return data
}

export type MasterResume = {
  id: number
  filename: string
  active: boolean
  status: string
  uploaded_at: string | null
  parsed_at: string | null
  file_size: number | null
  parse_error?: string | null
}

export async function fetchMasterResume(): Promise<{ resume: MasterResume | null; status: string }> {
  const { data } = await client.get("/api/resume")
  return data
}

export async function fetchResumeHistory(): Promise<{ resumes: MasterResume[] }> {
  const { data } = await client.get("/api/resumes")
  return data
}

export async function uploadMasterResume(file: File): Promise<{ resume: MasterResume; status: string }> {
  const form = new FormData()
  form.append("file", file)
  const { data } = await client.post("/api/resume", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  })
  return data
}

export async function removeMasterResume(): Promise<void> {
  await client.delete("/api/resume")
}

export function resumeFileUrl(id: number): string {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "")
  return `${base}/api/resume/file/${id}`
}
