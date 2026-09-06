import client from "./client"
import type { InterviewPrepResponse, InterviewEvalResponse } from "@/types/api"

export async function fetchInterviewPrep(params: {
  job_id?: number
  title?: string
  company?: string
  jd_text?: string
}): Promise<InterviewPrepResponse> {
  const { data } = await client.post<InterviewPrepResponse>("/api/interview/prep", params)
  return data
}

export async function evaluateInterviewAnswer(params: {
  question: string
  user_answer: string
  expected_topic?: string
}): Promise<InterviewEvalResponse> {
  const { data } = await client.post<InterviewEvalResponse>("/api/interview/evaluate", params)
  return data
}
