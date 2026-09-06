import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { ArrowLeft, FileText, Target, Users, Mail, CheckCircle, AlertTriangle, Clock } from "lucide-react"
import { Topbar } from "@/components/layout/topbar"
import { Card, CardHeader, CardTitle, CardContent, Badge, Button, Spinner } from "@/components/ui"
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
      const data = generate ? await generateStudio(Number(jobId)) : await fetchStudio(Number(jobId)).catch(() => generateStudio(Number(jobId)))
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
        // Idempotent: fetch existing and navigate
        try {
          const appsRes = await fetch("/api/applications").then(r=>r.json())
          const existing = appsRes.applications?.find((a:any)=>a.job_id===Number(jobId) && a.current_state!=="CLOSED")
          if (existing) { navigate(`/applications/${existing.id}`); return }
        } catch {}
      }
      alert(msg)
    } finally {
      setIsCreating(false)
    }
  }

  if (loading) return <><Topbar title="Application Studio" icon={<FileText className="h-5 w-5" />} /><div className="flex h-full items-center justify-center"><Spinner label="Building Studio…" /></div></>
  if (error) return <><Topbar title="Application Studio" icon={<FileText className="h-5 w-5" />} /><div className="p-6 text-sm text-red-500">{error}</div></>

  if (!studio) return null

  const job = studio.job || {}
  const priority = studio.priority || {}
  const match = studio.match || {}
  const isStale = studio.job_quality?.freshness_state === "STALE"

  return (
    <>
      <Topbar title="Application Studio" icon={<FileText className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}><ArrowLeft className="h-4 w-4" /> Back</Button>

        {/* Header */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">{job.title} <span className="text-text-muted">· {job.company}</span> {job.location && <span className="text-text-muted">· {job.location}</span>}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Badge variant={priority.tier==="HOT"?"accent": priority.tier==="WARM"?"amber": "neutral"}>{priority.tier || "UNKNOWN"}</Badge>
            <Badge variant="outline">Match {match.baseline?.final_score ?? job.fit_score ?? "—"}%</Badge>
            <Badge variant={isStale?"neutral":"outline"}>{studio.job_quality?.freshness_state || "UNKNOWN"}</Badge>
            {studio.job_quality?.is_duplicate && <Badge variant="outline">duplicate</Badge>}
            <Badge variant="outline">{studio.job_quality?.source_reliability || "neutral"}</Badge>
          </CardContent>
        </Card>

        {/* Why this job */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Target className="h-4 w-4" /> Why this job</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Matched: {(studio.skill_gaps||[]).filter((g:any)=>g.status==="SATISFIED").map((g:any)=>g.skill).join(", ") || "—"}</div>
            <div>Gaps: {(studio.skill_gaps||[]).filter((g:any)=>g.gap_type==="UNSUPPORTED").map((g:any)=>g.skill).join(", ") || "none unsupported"}</div>
            <div>Unknown: {(studio.skill_gaps||[]).filter((g:any)=>g.gap_type==="UNKNOWN").map((g:any)=>g.skill).join(", ") || "none"}</div>
            <div className="text-text-muted">Role {studio.components?.match} · Resume {studio.components?.resume}</div>
          </CardContent>
        </Card>

        {/* Resume — Tailoring Proposal */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-4 w-4" /> Resume — Tailoring Proposal</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>Status: <Badge variant={studio.resume_source?.status==="READY"?"neutral":"outline"}>{studio.resume_source?.status}</Badge> Proposal: <Badge variant={(studio.tailoring_proposal || studio.tailored_resume)?.status==="READY"?"accent": (studio.tailoring_proposal || studio.tailored_resume)?.status==="REQUIRES_REVIEW"?"amber":"outline"}>{(studio.tailoring_proposal || studio.tailored_resume)?.status}</Badge></div>
            {studio.resume_diff && <pre className="max-h-48 overflow-auto rounded border border-border bg-bg-secondary p-2 text-xs">{studio.resume_diff.unified?.slice(0,1500)}</pre>}
            {(studio.tailoring_proposal || studio.tailored_resume)?.preview && <div className="rounded border border-border bg-bg-secondary p-2 text-xs whitespace-pre-wrap">{(studio.tailoring_proposal || studio.tailored_resume).preview.slice(0,1000)}</div>}
            {studio.resume_diff?.unsupported_skills_not_inserted?.length>0 && <div className="text-amber flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> Unsupported not inserted: {studio.resume_diff.unsupported_skills_not_inserted.join(", ")}</div>}
            {studio.resume_diff?.unsupported_claims_detected?.length>0 && <div className="text-red-500 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> Unsupported claims detected: {studio.resume_diff.unsupported_claims_detected.join(", ")} — REQUIRES_REVIEW</div>}
            <label className="flex items-center gap-2"><input type="checkbox" checked={approvals.resume} onChange={e=>setApprovals({...approvals, resume:e.target.checked})} /> Approve tailoring proposal</label>
            <Button size="sm" onClick={()=>load(true)} disabled={loading || isCreating}>Regenerate</Button>
          </CardContent>
        </Card>

        {/* ATS — Requirement Coverage (not ATS score) */}
        <Card>
          <CardHeader><CardTitle>ATS — Requirement Coverage</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Status: <Badge variant={studio.ats?.status==="READY"?"accent":"outline"}>{studio.ats?.status}</Badge></div>
            {studio.ats?.details && (
              <>
                {studio.ats.details.ats_score == null ? <div className="text-text-muted">ATS score unavailable — showing requirement coverage</div> : <div>ATS Score: {studio.ats.details.ats_score}%</div>}
                <div>Requirement coverage: {studio.ats.details.requirement_coverage_percent ?? "—"}%</div>
                <div>Matched: {studio.ats.details.matched_keywords?.join(", ") || "—"}</div>
                <div>Missing (supported): {studio.ats.details.missing_supported?.join(", ") || "—"}</div>
                <div className="text-amber">Missing unsupported (do not claim): {studio.ats.details.missing_unsupported?.join(", ") || "—"}</div>
                <div className="text-text-muted">{studio.ats.details.recommendation}</div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Cover Letter */}
        <Card>
          <CardHeader><CardTitle>Cover Letter</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Status: <Badge variant={studio.cover_letter?.status==="READY"?"accent":"outline"}>{studio.cover_letter?.status}</Badge></div>
            {studio.cover_letter?.text && <div className="rounded border border-border bg-bg-secondary p-2 whitespace-pre-wrap text-xs">{studio.cover_letter.text.slice(0,1500)}</div>}
            <label className="flex items-center gap-2"><input type="checkbox" checked={approvals.cover} onChange={e=>setApprovals({...approvals, cover:e.target.checked})} /> Approve cover letter</label>
          </CardContent>
        </Card>

        {/* Recruiter */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-4 w-4" /> Recruiter</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Status: <Badge variant={studio.recruiter?.status==="FOUND"?"accent":"outline"}>{studio.recruiter?.status}</Badge></div>
            {studio.recruiter?.details && <div>{studio.recruiter.details.name} — {studio.recruiter.details.email} ({studio.recruiter.details.confidence}%)</div>}
            <div>Status: <Badge variant={studio.outreach_preview?.status==="READY"?"accent":"outline"}>{studio.outreach_preview?.status}</Badge></div>
            {studio.outreach_preview?.text && <div className="rounded border border-border bg-bg-secondary p-2 text-xs whitespace-pre-wrap">{studio.outreach_preview.text.slice(0,1000)}</div>}
            <div className="text-text-muted text-xs">Outreach is preview only — no auto-send.</div>
          </CardContent>
        </Card>

        {/* Autofill */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Clock className="h-4 w-4" /> Apply</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Autofill: <Badge variant="outline">{studio.autofill?.status}</Badge> — {studio.autofill?.detail}</div>
            <div>Resume: {approvals.resume ? <Badge variant="accent"><CheckCircle className="h-3 w-3" /> Approved</Badge> : <Badge variant="outline">Not ready</Badge>} Cover: {approvals.cover ? <Badge variant="accent">Approved</Badge> : <Badge variant="outline">Optional</Badge>}</div>
            <Button onClick={handleCreateApp} disabled={!approvals.resume || isCreating}>{isCreating ? "Creating…" : "Create Application (PREPARING)"}</Button>
            <div className="text-xs text-text-muted">Then mark APPLIED explicitly via Opportunities → Timeline. No auto-submit.</div>
            {studio.warnings?.length>0 && <div className="text-amber text-xs">Warnings: {studio.warnings.join("; ")}</div>}
            <div className="text-xs">Overall: <Badge variant={studio.overall_status==="COMPLETED"?"accent":"outline"}>{studio.overall_status}</Badge></div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}
