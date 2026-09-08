import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeft, FileText, Target, Users, Mail, CheckCircle2, AlertTriangle,
  Sparkles, RefreshCw, Send, ShieldAlert, Check, ChevronRight, Layers, Award
} from "lucide-react"
import { Topbar } from "@/components/layout/topbar"
import { Card, CardHeader, CardTitle, CardContent, Badge, Button, Spinner } from "@/components/ui"
import { PriorityBadge } from "@/components/ui/priority-badge"
import { MatchScore } from "@/components/ui/match-score"
import { EvidenceList } from "@/components/ui/evidence-list"
import { StepIndicator, getStudioSteps } from "@/components/ui/step-indicator"
import { cn } from "@/lib/utils"
import { generateStudio, fetchStudio } from "@/api/studio"
import { createApplication } from "@/api/applications"

export default function StudioPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [studio, setStudio] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [approvals, setApprovals] = useState({ resume: false, cover: false })
  const [isCreating, setIsCreating] = useState(false)

  const load = async (generate = false) => {
    if (!jobId) return
    setLoading(true)
    setError(null)
    try {
      const data = generate
        ? await generateStudio(Number(jobId))
        : await fetchStudio(Number(jobId)).catch(() => generateStudio(Number(jobId)))
      setStudio(data)
    } catch (e: any) {
      setError(e?.response?.data?.error || e.message || "Failed to load Studio")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(false) }, [jobId])

  const handleCreateApp = async () => {
    if (!jobId || isCreating) return
    setIsCreating(true)
    try {
      const app = await createApplication(Number(jobId))
      navigate(`/applications/${app.id}`)
    } catch (e: any) {
      const msg = e?.response?.data?.error || "Create failed"
      if (msg.includes("already exists")) {
        try {
          const appsRes = await fetch("/api/applications").then(r => r.json())
          const existing = appsRes.applications?.find((a: any) => a.job_id === Number(jobId) && a.current_state !== "CLOSED")
          if (existing) { navigate(`/applications/${existing.id}`); return }
        } catch { }
      }
      alert(msg)
    } finally {
      setIsCreating(false)
    }
  }

  if (loading) return (
    <>
      <Topbar title="Application Studio" icon={<FileText className="h-4 w-4 text-text-muted" />} />
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <Spinner label="Building Studio environment…" />
      </div>
    </>
  )

  if (error) return (
    <>
      <Topbar title="Application Studio" icon={<FileText className="h-4 w-4 text-text-muted" />} />
      <div className="p-8 max-w-xl mx-auto my-12 text-center rounded-xl border border-red-500/20 bg-red-500/5">
        <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-3" />
        <h3 className="text-base font-medium text-text-primary mb-1">Failed to load Application Studio</h3>
        <p className="text-xs text-text-muted mb-4">{error}</p>
        <Button size="sm" variant="outline" onClick={() => load()}>Retry Studio Build</Button>
      </div>
    </>
  )

  if (!studio) return null

  const job = studio.job || {}
  const priority = studio.priority || {}
  const match = studio.match || {}
  const isStale = studio.job_quality?.freshness_state === "STALE"
  const satisfiedGaps = (studio.skill_gaps || []).filter((g: any) => g.status === "SATISFIED")
  const unsupportedGaps = (studio.skill_gaps || []).filter((g: any) => g.gap_type === "UNSUPPORTED")

  return (
    <>
      <Topbar title="Application Studio" icon={<FileText className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">

        {/* Navigation & Header */}
        <div className="space-y-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="text-text-muted hover:text-text-primary px-0 hover:bg-transparent -ml-1"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1.5" /> Back to jobs
          </Button>

          <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-lg font-semibold text-text-primary tracking-tight">{job.title || "Untitled Role"}</h1>
                  <span className="text-text-faint">·</span>
                  <span className="text-sm font-medium text-text-secondary">{job.company || "Unknown Company"}</span>
                  {job.location && (
                    <>
                      <span className="text-text-faint">·</span>
                      <span className="text-xs text-text-muted">{job.location}</span>
                    </>
                  )}
                </div>
                <p className="text-xs text-text-muted">
                  Overall Studio Status: <span className="font-medium text-text-secondary">{studio.overall_status || "IN_PROGRESS"}</span>
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => load(true)} disabled={loading || isCreating} className="h-8 text-xs gap-1.5">
                  <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
                  Regenerate
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/50">
              <PriorityBadge tier={priority.tier || "UNKNOWN"} size="md" />
              <MatchScore score={match.baseline?.final_score ?? job.fit_score} label="Fit" showBar={false} size="sm" />
              <Badge variant={isStale ? "amber" : "outline"}>{studio.job_quality?.freshness_state || "FRESH"}</Badge>
              {studio.job_quality?.is_duplicate && <Badge variant="neutral">duplicate</Badge>}
              <Badge variant="outline">Source: {studio.job_quality?.source_reliability || "standard"}</Badge>
            </div>

            {/* Studio Step Progress */}
            <div className="pt-3 border-t border-border/30">
              <StepIndicator steps={getStudioSteps(studio, approvals)} />
            </div>
          </div>
        </div>

        {/* 2-Column Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Column: Tailoring & Content (2 cols wide on desktop) */}
          <div className="lg:col-span-2 space-y-6">

            {/* Why This Job / Skill Alignment */}
            <Card className="rounded-xl border-border">
              <CardHeader className="py-4">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Target className="h-3.5 w-3.5 text-accent" /> Why This Job & Skill Alignment
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <EvidenceList
                  items={[
                    ...satisfiedGaps.map((g: any) => ({ label: g.skill, status: "satisfied" as const })),
                    ...unsupportedGaps.map((g: any) => ({ label: g.skill, status: "missing" as const })),
                  ]}
                />

                <div className="flex items-center gap-4 text-[11px] text-text-muted pt-1">
                  <span>Role Match Score: <strong className="text-text-primary">{studio.components?.match ?? "—"}</strong></span>
                  <span>·</span>
                  <span>Resume Compatibility: <strong className="text-text-primary">{studio.components?.resume ?? "—"}</strong></span>
                </div>
              </CardContent>
            </Card>

            {/* Resume — Tailoring Proposal */}
            <Card className="rounded-xl border-border">
              <CardHeader className="py-4 flex flex-row items-center justify-between">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-accent" /> Resume Tailoring Proposal
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant={studio.resume_source?.status === "READY" ? "neutral" : "outline"}>
                    Source: {studio.resume_source?.status || "PENDING"}
                  </Badge>
                  <Badge variant={(studio.tailoring_proposal || studio.tailored_resume)?.status === "READY" ? "accent" : (studio.tailoring_proposal || studio.tailored_resume)?.status === "REQUIRES_REVIEW" ? "amber" : "outline"}>
                    {(studio.tailoring_proposal || studio.tailored_resume)?.status || "IDLE"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">

                {studio.resume_diff && (
                  <div>
                    <div className="text-[11px] font-medium text-text-secondary mb-1.5">Diff Highlights</div>
                    <pre className="max-h-40 overflow-auto rounded-lg border border-border/80 bg-black/30 p-3 text-[11px] font-mono text-text-secondary leading-relaxed">
                      {studio.resume_diff.unified?.slice(0, 1500)}
                    </pre>
                  </div>
                )}

                {(studio.tailoring_proposal || studio.tailored_resume)?.preview && (
                  <div>
                    <div className="text-[11px] font-medium text-text-secondary mb-1.5">Tailored Resume Preview</div>
                    <div className="max-h-48 overflow-auto rounded-lg border border-border/80 bg-bg-secondary p-3 text-[11px] font-mono text-text-muted leading-relaxed whitespace-pre-wrap">
                      {(studio.tailoring_proposal || studio.tailored_resume).preview.slice(0, 1000)}
                    </div>
                  </div>
                )}

                {studio.resume_diff?.unsupported_skills_not_inserted?.length > 0 && (
                  <div className="flex items-center gap-2 text-amber text-[11px] p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>Unsupported skills omitted: {studio.resume_diff.unsupported_skills_not_inserted.join(", ")}</span>
                  </div>
                )}

                {studio.resume_diff?.unsupported_claims_detected?.length > 0 && (
                  <div className="flex items-center gap-2 text-coral text-[11px] p-2.5 rounded-lg bg-coral/5 border border-coral/20">
                    <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
                    <span>Unsupported claims detected: {studio.resume_diff.unsupported_claims_detected.join(", ")} — REQUIRES REVIEW</span>
                  </div>
                )}

                <div className="pt-2 flex items-center justify-between border-t border-border/50">
                  <label className="flex items-center gap-2.5 text-xs text-text-primary cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={approvals.resume}
                      onChange={e => setApprovals({ ...approvals, resume: e.target.checked })}
                      className="rounded border-border bg-bg-secondary text-accent focus:ring-accent/20 h-4 w-4"
                    />
                    <span>Approve tailored resume proposal</span>
                  </label>

                  {approvals.resume && (
                    <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Approved
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Cover Letter */}
            <Card className="rounded-xl border-border">
              <CardHeader className="py-4 flex flex-row items-center justify-between">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-accent" /> Generated Cover Letter
                </CardTitle>
                <Badge variant={studio.cover_letter?.status === "READY" ? "accent" : "outline"}>
                  {studio.cover_letter?.status || "NOT_GENERATED"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                {studio.cover_letter?.text ? (
                  <div className="max-h-48 overflow-auto rounded-lg border border-border/80 bg-bg-secondary p-3 text-[11px] text-text-secondary leading-relaxed whitespace-pre-wrap">
                    {studio.cover_letter.text.slice(0, 1500)}
                  </div>
                ) : (
                  <div className="p-4 text-center text-text-faint text-xs rounded-lg border border-dashed border-border/60">
                    No cover letter generated for this role yet.
                  </div>
                )}

                <div className="pt-2 flex items-center justify-between border-t border-border/50">
                  <label className="flex items-center gap-2.5 text-xs text-text-primary cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={approvals.cover}
                      onChange={e => setApprovals({ ...approvals, cover: e.target.checked })}
                      className="rounded border-border bg-bg-secondary text-accent focus:ring-accent/20 h-4 w-4"
                    />
                    <span>Approve cover letter (Optional)</span>
                  </label>

                  {approvals.cover && (
                    <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Approved
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Column: ATS Coverage, Recruiter, Action (1 col wide on desktop) */}
          <div className="space-y-6">

            {/* ATS Requirement Coverage */}
            <Card className="rounded-xl border-border">
              <CardHeader className="py-4 flex flex-row items-center justify-between">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Award className="h-3.5 w-3.5 text-accent" /> ATS Requirement Coverage
                </CardTitle>
                <Badge variant={studio.ats?.status === "READY" ? "accent" : "outline"}>
                  {studio.ats?.status || "PENDING"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {studio.ats?.details ? (
                  <>
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-border/60 space-y-2">
                      {studio.ats.details.ats_score == null ? (
                        <div className="text-[11px] text-text-muted">ATS score unavailable — displaying requirement coverage</div>
                      ) : (
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-text-muted">Estimated ATS Score</span>
                          <span className="font-semibold text-text-primary">{studio.ats.details.ats_score}%</span>
                        </div>
                      )}
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-text-muted">Requirement Coverage</span>
                        <span className="font-semibold text-emerald-400">{studio.ats.details.requirement_coverage_percent ?? "—"}%</span>
                      </div>
                    </div>

                    <div className="space-y-1.5 text-[11px]">
                      <div>
                        <span className="text-text-muted">Matched Keywords: </span>
                        <span className="text-text-secondary">{studio.ats.details.matched_keywords?.join(", ") || "—"}</span>
                      </div>
                      <div>
                        <span className="text-text-muted">Missing (Supported): </span>
                        <span className="text-text-secondary">{studio.ats.details.missing_supported?.join(", ") || "None"}</span>
                      </div>
                      {studio.ats.details.missing_unsupported?.length > 0 && (
                        <div className="text-amber">
                          <span>Missing Unsupported: </span>
                          <span>{studio.ats.details.missing_unsupported?.join(", ")}</span>
                        </div>
                      )}
                    </div>

                    {studio.ats.details.recommendation && (
                      <p className="text-[11px] text-text-faint italic border-t border-border/40 pt-2">
                        "{studio.ats.details.recommendation}"
                      </p>
                    )}
                  </>
                ) : (
                  <div className="text-text-faint text-xs">No ATS audit details available yet.</div>
                )}
              </CardContent>
            </Card>

            {/* Recruiter Outreach */}
            <Card className="rounded-xl border-border">
              <CardHeader className="py-4 flex flex-row items-center justify-between">
                <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Users className="h-3.5 w-3.5 text-accent" /> Recruiter Contact & Outreach
                </CardTitle>
                <Badge variant={studio.recruiter?.status === "FOUND" ? "accent" : "outline"}>
                  {studio.recruiter?.status || "NOT_FOUND"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {studio.recruiter?.details && (
                  <div className="p-2.5 rounded-lg bg-white/[0.02] border border-border/60 text-xs space-y-1">
                    <div className="font-medium text-text-primary">{studio.recruiter.details.name}</div>
                    <div className="text-text-muted text-[11px]">{studio.recruiter.details.email}</div>
                    <div className="text-[10px] text-text-faint">Match confidence: {studio.recruiter.details.confidence}%</div>
                  </div>
                )}

                {studio.outreach_preview?.text && (
                  <div>
                    <div className="text-[11px] font-medium text-text-muted mb-1">Outreach Message Preview</div>
                    <div className="p-2.5 rounded-lg bg-bg-secondary border border-border/60 text-[11px] text-text-muted whitespace-pre-wrap max-h-32 overflow-auto">
                      {studio.outreach_preview.text.slice(0, 1000)}
                    </div>
                  </div>
                )}

                <div className="text-[10px] text-text-faint italic">
                  Note: Outreach is preview-only. No automated emails are sent.
                </div>
              </CardContent>
            </Card>

            {/* Final Action Card */}
            <Card className="rounded-xl border-accent/30 bg-accent/[0.02]">
              <CardHeader className="py-4">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-accent flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-accent" /> Application Action
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="space-y-1 text-[11px] text-text-muted">
                  <div className="flex justify-between">
                    <span>Resume Tailoring:</span>
                    <span className={approvals.resume ? "text-emerald-400 font-medium" : "text-amber"}>
                      {approvals.resume ? "Approved" : "Requires Approval"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Cover Letter:</span>
                    <span className={approvals.cover ? "text-emerald-400 font-medium" : "text-text-faint"}>
                      {approvals.cover ? "Approved" : "Optional"}
                    </span>
                  </div>
                </div>

                <Button
                  className="w-full h-9 text-xs font-medium"
                  onClick={handleCreateApp}
                  disabled={!approvals.resume || isCreating}
                >
                  {isCreating ? "Creating Application…" : "Create Application (PREPARING)"}
                </Button>

                <p className="text-[10px] text-text-faint text-center leading-relaxed">
                  Creates application record in <strong>PREPARING</strong> state. Mark as <strong>APPLIED</strong> manually in Opportunities after submitting.
                </p>

                {studio.warnings?.length > 0 && (
                  <div className="text-coral text-[10px] pt-1">
                    Warnings: {studio.warnings.join("; ")}
                  </div>
                )}
              </CardContent>
            </Card>

          </div>
        </div>

      </div>
    </>
  )
}
