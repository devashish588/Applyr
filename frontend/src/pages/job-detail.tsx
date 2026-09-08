import { useParams, useNavigate, Link } from "react-router-dom"
import { useJobDetail } from "@/hooks/use-jobs"
import { useApplications } from "@/hooks/use-applications"
import { Topbar } from "@/components/layout/topbar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { PriorityBadge } from "@/components/ui/priority-badge"
import { MatchScore } from "@/components/ui/match-score"
import { EvidenceList } from "@/components/ui/evidence-list"
import { getNextActionForJob } from "@/lib/next-action"
import { ArrowLeft, ExternalLink, Sparkles, Target, AlertTriangle, Building, MapPin } from "lucide-react"

function derivePriority(score: number | null | undefined): string {
  const s = score ?? 0
  if (s >= 80) return "HOT"
  if (s >= 65) return "WARM"
  if (s >= 45) return "REVIEW"
  return "COLD"
}

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

  if (isLoading) return (
    <>
      <Topbar title="Job Intelligence Detail" icon={<Target className="h-4 w-4 text-text-muted" />} />
      <div className="p-6 max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-8 w-1/3 rounded-lg" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    </>
  )

  if (isError || !job || !job.id) return (
    <>
      <Topbar title="Job Intelligence Detail" icon={<Target className="h-4 w-4 text-text-muted" />} />
      <div className="p-12 max-w-md mx-auto text-center space-y-3">
        <p className="text-sm text-text-primary">Job detail record unavailable.</p>
        <Button size="sm" variant="outline" onClick={() => navigate(-1)}>Back to Discover</Button>
      </div>
    </>
  )

  const match = hookMatch || (job.match_details_json ? (() => { try { return JSON.parse(job.match_details_json) } catch { return null } })() : null)
  const priority = (job as any).priority_tier || (job as any).priority || hookMatch?.priority_tier

  return (
    <>
      <Topbar title="Job Intelligence Detail" icon={<Target className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto space-y-6">

        {/* Back Navigation & Main Card */}
        <div className="space-y-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="text-text-muted hover:text-text-primary px-0 hover:bg-transparent -ml-1 text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1.5" /> Back to jobs
          </Button>

          <Card className="rounded-xl border-border bg-bg-secondary p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-lg font-semibold text-text-primary tracking-tight mb-1">{job.title}</h1>
                <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
                  <span className="font-medium text-text-secondary flex items-center gap-1">
                    <Building className="h-3 w-3" /> {job.company}
                  </span>
                  {job.location && (
                    <>
                      <span>·</span>
                      <span className="flex items-center gap-1"><MapPin className="h-3 w-3" /> {job.location}</span>
                    </>
                  )}
                  {job.salary && <span>· {job.salary}</span>}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <PriorityBadge tier={priority || derivePriority(job.fit_score)} size="md" />
                {job.freshness_state && <Badge variant="outline">{job.freshness_state}</Badge>}
                {job.is_duplicate_of && <Badge variant="neutral">Linked Duplicate</Badge>}
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-2 border-t border-border/40">
              {job.url && (
                <a href={job.url} target="_blank" rel="noreferrer">
                  <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5">
                    <ExternalLink className="h-3.5 w-3.5" /> Posting Link
                  </Button>
                </a>
              )}
              <Link to={`/studio/${job.id}`}>
                <Button size="sm" className="h-8 text-xs gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> Prepare Application in Studio
                </Button>
              </Link>
              {application && (
                <Link to={`/applications/${application.id}`}>
                  <Button variant="secondary" size="sm" className="h-8 text-xs">
                    View Active Application
                  </Button>
                </Link>
              )}
            </div>
          </Card>
        </div>

        {/* Next Action Banner */}
        {next && (
          <div className="rounded-xl border border-accent/30 bg-accent/[0.03] p-4 text-xs flex items-center justify-between">
            <div>
              <span className="font-semibold text-accent block">Recommended Action: {next.label}</span>
              <span className="text-text-muted">{next.description}</span>
            </div>
          </div>
        )}

        {/* 2-Column Intelligence Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Match Score & Priority Breakdown */}
          <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-3">
            <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Compatibility Audit</div>
            <MatchScore score={match?.final_score ?? job.fit_score} label="Overall Fit" showBar={true} size="lg" />
            {match?.explanation && (
              <p className="text-xs text-text-secondary leading-relaxed bg-white/[0.01] p-3 rounded-lg border border-border/40">
                {match.explanation}
              </p>
            )}
          </div>

          {/* Recommended Reasons & Gaps */}
          <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
            <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Skill Alignment & Gaps</div>
            <EvidenceList
              items={[
                ...(match?.matched_skills || match?.skills_to_highlight || []).map((s: string) => ({ label: s, status: "satisfied" as const })),
                ...(match?.missing_skills || []).map((s: string) => ({ label: s, status: "missing" as const })),
              ]}
            />
            {(!match?.matched_skills?.length && !match?.skills_to_highlight?.length && !match?.missing_skills?.length) && (
              <p className="text-xs text-text-faint">No detailed skill alignment data available yet.</p>
            )}
          </div>

        </div>

        {/* Job Description Requirements */}
        <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-3">
          <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Role Description Snippet</div>
          <p className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap bg-black/20 p-4 rounded-lg border border-border/60 max-h-60 overflow-auto font-mono">
            {job.jd_text?.slice(0, 800) || "No job description text available."}
          </p>
        </div>

        {application && (
          <div className="rounded-xl border border-border bg-bg-secondary p-4 text-xs flex justify-between items-center">
            <span className="text-text-muted">Application Record Status:</span>
            <span className="font-semibold text-accent">{application.current_state} {application.final_outcome ? `· ${application.final_outcome}` : ""}</span>
          </div>
        )}

      </div>
    </>
  )
}
