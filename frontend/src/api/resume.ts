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
