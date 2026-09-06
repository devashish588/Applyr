import { useParams, useNavigate, Link } from "react-router-dom"
import { useJobDetail } from "@/hooks/use-jobs"
import { useApplications } from "@/hooks/use-applications"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { getNextActionForJob } from "@/lib/next-action"

export default function JobDetailPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const id = jobId ? parseInt(jobId, 10) : null
  const { data, isLoading, isError } = useJobDetail(id)
  const job: any = (data as any)?.job || (data as any)
  const hookMatch: any = (data as any)?.match
  const { data: apps } = useApplications()
  const application = apps?.find((a: any) => a.job_id === id) || null
  const next = job ? getNextActionForJob(job, application) : null

  if (isLoading) return <div className="p-6 space-y-4"><Skeleton className="h-8 w-1/2" /><Skeleton className="h-32 w-full" /></div>
  if (isError || !job) return <div className="p-6"><p className="text-sm text-text-muted">Something went wrong. Try again.</p><Button variant="ghost" onClick={() => navigate(-1)} className="mt-4">Go back</Button></div>
  if (!job || !job.id) return <div className="p-6"><p className="text-sm">Job not found</p></div>

  const match = hookMatch || (job.match_details_json ? (() => { try { return JSON.parse(job.match_details_json) } catch { return null } })() : null)
  const priority = (job as any).priority_tier || (job as any).priority || hookMatch?.priority_tier

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <Button variant="ghost" onClick={() => navigate(-1)}>← Back</Button>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>{job.title}</span>
            <Badge variant={job.is_duplicate_of ? "amber" : "neutral"}>{job.is_duplicate_of ? "Duplicate / Linked" : job.freshness_state || "UNKNOWN"}</Badge>
          </CardTitle>
          <div className="text-sm text-text-muted">{job.company} · {job.location || "UNKNOWN"} · {job.source || "UNKNOWN"} {job.salary ? `· ${job.salary}` : ""}</div>
          <div className="flex gap-2 mt-2">
            {job.freshness_state && <Badge variant="outline">{job.freshness_state}</Badge>}
            {priority && <Badge variant={priority === "HOT" ? "green" : priority === "WARM" ? "amber" : "neutral"}>{priority}</Badge>}
            {job.source && <Badge variant="outline">{job.source}</Badge>}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <a href={job.url} target="_blank" rel="noreferrer"><Button variant="outline">View posting</Button></a>
            <Link to={`/studio/${job.id}`}><Button>Prepare Application</Button></Link>
            {application && <Link to={`/applications/${application.id}`}><Button variant="secondary">View Application</Button></Link>}
          </div>

          {next && (
            <div className="rounded border border-border bg-bg-secondary p-3 text-sm">
              <span className="font-medium">Next:</span> {next.label} — {next.description}
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="text-sm font-semibold">Match Score</h4>
              {match?.final_score != null ? (
                <div className="text-2xl font-bold">{match.final_score}</div>
              ) : (
                <p className="text-sm text-text-muted">Match explanation unavailable</p>
              )}
              {match?.explanation && <p className="text-sm mt-1">{match.explanation}</p>}
            </div>
            <div>
              <h4 className="text-sm font-semibold">Priority</h4>
              <p className="text-sm">{priority || "REVIEW"}</p>
              {job.match_details_json && <p className="text-xs text-text-muted mt-1">Based on score, freshness, source, recruiter</p>}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold">Why this is recommended</h4>
            {match?.explanation ? (
              <ul className="list-disc pl-5 text-sm">
                <li>Skill alignment: {match.skill_match || "UNKNOWN"}</li>
                <li>Experience: {match.experience_match || "UNKNOWN"}</li>
                <li>Role: {match.role_match || "UNKNOWN"}</li>
              </ul>
            ) : (
              <p className="text-sm text-text-muted">Match explanation unavailable</p>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold">Gaps</h4>
            {match?.missing_skills?.length ? (
              <ul className="list-disc pl-5 text-sm">
                {match.missing_skills.slice(0, 5).map((s: string) => <li key={s}>{s}</li>)}
              </ul>
            ) : (
              <p className="text-sm text-text-muted">No gaps found or UNKNOWN</p>
            )}
          </div>

          <div>
            <h4 className="text-sm font-semibold">Requirements</h4>
            <p className="text-sm whitespace-pre-wrap">{job.jd_text?.slice(0, 600) || "No description"}</p>
          </div>

          {application && (
            <div className="rounded border p-3 text-sm">
              <span className="font-medium">Application:</span> {application.current_state} {application.final_outcome ? `· ${application.final_outcome}` : ""}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
