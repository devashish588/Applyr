import { useState, useEffect } from "react"
import { Briefcase, GripVertical, MoreHorizontal, ChevronDown, Clock, FileText, User } from "lucide-react"
import { Spinner } from "@/components/ui"
import { AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { useJobs, useUpdateJobCompany, usePrioritizedJobs } from "@/hooks/use-jobs"
import { Button, Badge, Tooltip, Modal, Input, EmptyState } from "@/components/ui"
import { cn, sanitizeCompany, scoreColor, statusLabel } from "@/lib/utils"
import { fetchApplications, fetchApplicationTimeline } from "@/api/applications"
import { fetchInterviews, fetchFollowUps } from "@/api/interviews"
import type { Job } from "@/types/api"

const COLUMNS = [
  { key: "found", label: "Discovered", color: "text-blue", dot: "bg-blue" },
  { key: "draft", label: "Drafted", color: "text-accent-sub", dot: "bg-accent" },
  { key: "ready", label: "Ready", color: "text-amber", dot: "bg-amber" },
  { key: "sent", label: "Applied", color: "text-green", dot: "bg-green" },
] as const

type ColumnKey = (typeof COLUMNS)[number]["key"]

export default function OpportunitiesPage() {
  const [sortBy, setSortBy] = useState<"priority" | "score" | "freshness">("priority")
  const { data: jobs, isLoading } = useJobs()
  const { data: prioritized } = usePrioritizedJobs(sortBy === "priority")
  const updateCompany = useUpdateJobCompany()
  const displayJobs = sortBy === "priority" && prioritized ? prioritized.map((p: any) => ({ ...p.job, priority: p.priority, baseline_analysis: p.baseline_analysis })) : jobs

  // Local status override map (client-side kanban movement)
  const [statusOverrides, setStatusOverrides] = useState<Record<number, ColumnKey>>({})
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const [overColumn, setOverColumn] = useState<ColumnKey | null>(null)

  const getStatus = (job: Job): ColumnKey => {
    const status = String(job.status || "found").toLowerCase()
    if (status in statusOverrides || COLUMNS.some((c) => c.key === status)) {
      return statusOverrides[job.id] || (status as ColumnKey)
    }
    return "found"
  }

  const sortedJobs = (() => {
    const list = [...(displayJobs || [])]
    if (sortBy === "score") list.sort((a: any, b: any) => (b.fit_score || 0) - (a.fit_score || 0))
    if (sortBy === "freshness") list.sort((a: any, b: any) => new Date((b as any).last_seen_at || b.discovered_at || b.scraped_at || 0).getTime() - new Date((a as any).last_seen_at || a.discovered_at || a.scraped_at || 0).getTime())
    return list
  })()

  const buckets: Record<ColumnKey, Job[]> = { found: [], draft: [], ready: [], sent: [] }
  for (const job of sortedJobs || []) {
    buckets[getStatus(job as Job)].push(job as Job)
  }

  const changeStatus = (id: number, next: ColumnKey) => {
    setStatusOverrides((prev) => ({ ...prev, [id]: next }))
  }

  const handleDrop = (targetColumn: ColumnKey) => {
    if (draggingId != null) {
      changeStatus(draggingId, targetColumn)
    }
    setDraggingId(null)
    setOverColumn(null)
  }

  const columns: ColumnKey[] = ["found", "draft", "ready", "sent"]

  return (
    <>
      <Topbar title="Applications" icon={<Briefcase className="h-5 w-5" />} />
      <div className="flex gap-2 px-4 pt-2">
        <Button size="sm" variant={sortBy === "priority" ? "primary" : "ghost"} onClick={() => setSortBy("priority")}>Priority</Button>
        <Button size="sm" variant={sortBy === "score" ? "primary" : "ghost"} onClick={() => setSortBy("score")}>Match Score</Button>
        <Button size="sm" variant={sortBy === "freshness" ? "primary" : "ghost"} onClick={() => setSortBy("freshness")}>Freshness</Button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-text-muted">
            <Spinner label="Loading applications…" />
          </div>
        ) : jobs && jobs.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No applications yet"
            description="Run a discovery to populate your application board."
          />
        ) : (
          <Board
            columns={columns}
            buckets={buckets}
            draggingId={draggingId}
            setDraggingId={setDraggingId}
            overColumn={overColumn}
            setOverColumn={setOverColumn}
            onDrop={handleDrop}
            onEditCompany={updateCompany.mutate}
          />
        )}
      </div>
    </>
  )
}

function Board({
  columns, buckets, draggingId, setDraggingId, overColumn, setOverColumn, onDrop, onEditCompany,
}: {
  columns: ColumnKey[]
  buckets: Record<ColumnKey, Job[]>
  draggingId: number | null
  setDraggingId: (id: number | null) => void
  overColumn: ColumnKey | null
  setOverColumn: (value: React.SetStateAction<ColumnKey | null>) => void
  onDrop: (target: ColumnKey) => void
  onEditCompany: (args: { jobId: number; company: string }) => void
}) {
  const [editJob, setEditJob] = useState<Job | null>(null)
  const [companyDraft, setCompanyDraft] = useState("")

  return (
    <div className="flex h-full gap-3 overflow-x-auto">
      {columns.map((key) => {
        const col = COLUMNS.find((c) => c.key === key)!
        const items = buckets[key]
        return (
          <div
            key={key}
            onDragOver={(e) => { e.preventDefault(); setOverColumn(key) }}
            onDragLeave={() => setOverColumn((c) => (c === key ? null : c))}
            onDrop={(e) => { e.preventDefault(); onDrop(key) }}
            className={cn(
              "flex min-w-[240px] max-w-[300px] flex-1 flex-col rounded-lg border transition-colors",
              overColumn === key ? "border-accent bg-accent/[0.03]" : "border-border bg-bg-secondary"
            )}
          >
            {/* Header */}
            <div
              className="flex items-center gap-2 border-b border-border px-3.5 py-3"
              onDrop={(e) => { e.preventDefault(); onDrop(key) }}
            >
              <span className={cn("h-2 w-2 rounded-full", col.dot)} />
              <span className={cn("text-[11px] font-semibold uppercase tracking-wider", col.color)}>{col.label}</span>
              <span className="ml-auto rounded-full bg-bg-tertiary px-2 py-0.5 text-[10px] font-semibold text-text-muted">
                {items.length}
              </span>
            </div>

            {/* Cards */}
            <div className="flex flex-1 flex-col gap-1.5 overflow-y-auto p-1.5">
              <AnimatePresence>
                {items.length === 0 ? (
                  <div className={cn("rounded-md border border-dashed py-10 text-center text-[11px] text-text-muted", overColumn === key && "border-accent")}>
                    Drop here
                  </div>
                ) : (
                  items.map((job) => (
                    <BoardCard
                      key={job.id}
                      job={job}
                      isDragging={draggingId === job.id}
                      onDragStart={() => setDraggingId(job.id)}
                      onDragEnd={() => setDraggingId(null)}
                      onEditCompany={() => { setEditJob(job); setCompanyDraft(job.company || "") }}
                    />
                  ))
                )}
              </AnimatePresence>
            </div>
          </div>
        )
      })}

      {/* Company edit modal */}
      <Modal
        open={!!editJob}
        onClose={() => setEditJob(null)}
        title="Edit Company"
        size="sm"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setEditJob(null)}>Cancel</Button>
            <Button
              onClick={() => {
                if (editJob) {
                  onEditCompany({ jobId: editJob.id, company: companyDraft })
                  setEditJob(null)
                }
              }}
            >
              Save
            </Button>
          </div>
        }
      >
        {editJob && (
          <div className="space-y-3">
            <div>
              <div className="text-[12px] font-medium text-text-secondary">{editJob.title || "Role"}</div>
              <div className="text-[11px] text-text-muted">Update the company name for this job.</div>
            </div>
            <Input
              value={companyDraft}
              onChange={(e) => setCompanyDraft(e.target.value)}
              placeholder="Company name"
              autoFocus
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

function BoardCard({
  job, isDragging, onDragStart, onDragEnd, onEditCompany,
}: {
  job: Job
  isDragging: boolean
  onDragStart: () => void
  onDragEnd: () => void
  onEditCompany: () => void
}) {
  const score = job.fit_score || 0
  const priority: any = (job as any).priority
  const [showEvidence, setShowEvidence] = useState(false)
  const [showTimeline, setShowTimeline] = useState(false)
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={cn(
        "group cursor-grab rounded-md border bg-bg p-3 transition-all active:cursor-grabbing",
        isDragging ? "border-accent opacity-40 shadow-lg" : "border-border hover:-translate-y-0.5 hover:border-border-hover hover:shadow-md hover:shadow-black/20"
      )}
    >
      <div className="flex items-start gap-2">
        <GripVertical className="mt-0.5 h-3.5 w-3.5 shrink-0 text-text-muted opacity-0 transition group-hover:opacity-100" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-[12px] font-semibold text-text-primary">{sanitizeCompany(job.company)}</span>
            {job.needs_review === 1 && <Badge variant="amber" className="px-1 py-0 text-[9px]">?</Badge>}
            {priority && (
              <Tooltip content={priority.explanation || priority.tier} side="top">
                <Badge variant={priority.tier === "HOT" ? "accent" : priority.tier === "WARM" ? "amber" : priority.tier === "COLD" ? "neutral" : "outline"} className="px-1 py-0 text-[9px]">{priority.tier}</Badge>
              </Tooltip>
            )}
            {(job as any).freshness_state && (
              <Tooltip content={`Freshness: ${(job as any).freshness_state} — scraped ${job.scraped_at ? new Date(job.scraped_at).toLocaleDateString() : "unknown"}`} side="top">
                <Badge variant={(job as any).freshness_state === "STALE" ? "neutral" : (job as any).freshness_state === "AGING" ? "amber" : (job as any).freshness_state === "NEW" ? "accent" : "outline"} className="px-1 py-0 text-[9px]">{(job as any).freshness_state}</Badge>
              </Tooltip>
            )}
            {(job as any).is_duplicate && <Badge variant="outline" className="px-1 py-0 text-[9px]">duplicate</Badge>}
          </div>
          <div className="truncate text-[13px] text-text-secondary">{job.title || "Role"}</div>
        </div>
        <Tooltip content="Edit company" side="top">
          <button onClick={(e) => { e.stopPropagation(); onEditCompany() }} className="rounded p-0.5 text-text-muted opacity-0 transition hover:bg-surface-hover hover:text-text-primary group-hover:opacity-100">
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        </Tooltip>
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <span className={cn("text-[11px] font-bold", scoreColor(score))}>{score}%</span>
        <Badge variant={job.needs_review === 1 ? "amber" : "neutral"}>{statusLabel(job.status || "found")}</Badge>
      </div>
      <a href={`/studio/${job.id}`} onClick={(e)=>e.stopPropagation()} className="mt-1 block rounded bg-accent py-1 text-center text-[10px] font-medium text-white">Studio</a>
      <button onClick={() => setShowTimeline(!showTimeline)} className="mt-1 flex w-full items-center justify-center gap-1 rounded bg-bg-secondary py-1 text-[10px] text-text-muted hover:text-text-primary">Timeline</button>
      {showTimeline && <ApplicationDetailPanel jobId={job.id} />}
      <button onClick={() => setShowEvidence(!showEvidence)} className="mt-2 flex w-full items-center justify-center gap-1 rounded bg-bg-secondary py-1 text-[10px] text-text-muted hover:text-text-primary">
        <ChevronDown className={cn("h-3 w-3 transition", showEvidence && "rotate-180")} /> {showEvidence ? "Hide" : "Evidence"}
      </button>
      {showEvidence && <MatchEvidencePanel jobId={job.id} />}
    </div>
  )
}

function TimelinePanel({ jobId }: { jobId: number }) {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetchApplicationTimeline(jobId)
      .then((data) => { setEvents(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [jobId])
  if (loading) return <div className="mt-2 text-[10px] text-text-muted">Loading timeline…</div>
  if (events.length === 0) return <div className="mt-2 text-[10px] text-text-muted">No events yet</div>
  const eventIcon = (type: string) => {
    if (type.includes("submitted") || type.includes("applied")) return <Clock className="h-3 w-3 text-green" />
    if (type.includes("note")) return <FileText className="h-3 w-3 text-accent" />
    return <User className="h-3 w-3 text-text-muted" />
  }
  return (
    <div className="mt-2 space-y-1 rounded border border-border bg-bg-secondary p-2">
      {events.map((ev, i) => (
        <div key={ev.id || i} className="flex items-start gap-2 text-[10px]">
          {eventIcon(ev.event_type)}
          <div className="min-w-0 flex-1">
            <span className="font-medium text-text-secondary">{ev.event_type}</span>
            <span className="ml-1 text-text-muted">by {ev.actor || "user"}</span>
            {ev.timestamp && <div className="text-[9px] text-text-muted">{new Date(ev.timestamp).toLocaleString()}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

function ApplicationDetailPanel({ jobId }: { jobId: number }) {
  const [app, setApp] = useState<any>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [interviews, setInterviews] = useState<any[]>([])
  const [followUps, setFollowUps] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    Promise.all([
      fetchApplications().then((apps:any[])=> apps.find((a:any)=> a.job_id===jobId) || null).catch(()=>null),
      fetchApplicationTimeline(jobId).catch(()=>[]),
    ]).then(async ([foundApp, tl])=>{
      if (foundApp) {
        setApp(foundApp)
        setTimeline(tl)
        try { setInterviews(await fetchInterviews(foundApp.id)) } catch {}
        try { setFollowUps(await fetchFollowUps(foundApp.id)) } catch {}
      } else {
        setTimeline(tl)
      }
      setLoading(false)
    })
  }, [jobId])
  if (loading) return <div className="mt-2 text-[10px] text-text-muted">Loading application…</div>
  if (!app) return <TimelinePanel jobId={jobId} />
  const nextAction: Record<string,string> = {
    PREPARING: "Complete preparation",
    READY_TO_APPLY: "Apply now",
    APPLIED: "Follow up after 5–7 days",
    SCREENING: "Await screening — Prepare for interview",
    INTERVIEW: "Prepare technical interview",
    FINAL: "Prepare final interview",
    OFFER: "Review offer",
    CLOSED: `Closed — ${app.current_state} ${timeline.find((e:any)=>e.event_type==="closed")?.payload || ""}`,
  }
  return (
    <div className="mt-2 space-y-2 rounded border border-border bg-bg-secondary p-2">
      <div className="flex items-center justify-between text-[10px]">
        <span className="font-semibold text-text-primary">{app.current_state}</span>
        <span className="text-text-muted">Next: {nextAction[app.current_state] || "—"}</span>
      </div>
      <div className="space-y-1">
        {timeline.slice(-5).map((ev:any,i:number)=>(
          <div key={ev.id||i} className="flex items-center gap-2 text-[10px] text-text-muted">
            <Clock className="h-3 w-3" /> {ev.event_type} <span className="text-[9px]">{ev.timestamp ? new Date(ev.timestamp).toLocaleDateString() : ""}</span>
          </div>
        ))}
      </div>
      {interviews.length>0 && <div className="text-[10px]">Interviews: {interviews.map((iv:any)=>`${iv.stage} ${iv.status}`).join(", ")}</div>}
      {followUps.length>0 && <div className="text-[10px]">Follow-ups: {followUps.map((f:any)=>`${f.follow_up_type} ${f.status}`).join(", ")}</div>}
      <div className="flex gap-1">
        <a href={`/studio/${jobId}`} className="rounded bg-accent px-2 py-1 text-[10px] text-white">Interview Prep</a>
        <button onClick={()=> fetch(`/api/applications/${app.id}/interview-prep`).then(r=>r.json()).then(j=> alert(JSON.stringify(j.prep?.kit?.behavioral_questions?.[0] || j.prep || "No prep")))} className="rounded border border-border px-2 py-1 text-[10px]">Prep</button>
      </div>
    </div>
  )
}

function MatchEvidencePanel({ jobId }: { jobId: number }) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetch(`/api/jobs/${jobId}/match`)
      .then((r) => r.json())
      .then((j) => {
        setData(j.match_result || j.match || null)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [jobId])
  if (loading) return <div className="mt-2 text-[10px] text-text-muted">Loading evidence…</div>
  if (!data) return <div className="mt-2 text-[10px] text-text-muted">No evidence</div>
  const rows: Array<{ label: string; evals: any[] }> = [
    { label: "Skills", evals: data.requirement_evaluations || [] },
    { label: "Experience", evals: data.experience_evaluations || [] },
    { label: "Role", evals: data.role_evaluations || [] },
    { label: "Location", evals: data.location_evaluations || [] },
    { label: "Seniority", evals: data.seniority_evaluations || [] },
  ]
  return (
    <div className="mt-2 space-y-1 rounded border border-border bg-bg-secondary p-2">
      {rows.map((row) => {
        const status = row.evals.length === 0 ? "NO_REQUIREMENT" : row.evals[0]?.status || "UNKNOWN"
        const color = status === "satisfied" || status === "SATISFIED" ? "text-green" : status === "missing" || status === "MISSING" ? "text-amber" : "text-text-muted"
        return (
          <div key={row.label} className="flex items-center justify-between text-[10px]">
            <span className="font-medium text-text-secondary">{row.label}</span>
            <span className={cn("rounded px-1.5 py-0.5 text-[9px] font-semibold", color, status === "UNKNOWN" ? "bg-bg-tertiary" : "bg-bg")}>{status}</span>
          </div>
        )
      })}
      <div className="pt-1 text-[9px] text-text-muted">Evidence: {data.requirement_evaluations?.[0]?.relationship_type || data.experience_evaluations?.[0]?.evidence_source || "provenance preserved"}</div>
    </div>
  )
}