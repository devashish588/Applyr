import { useState } from "react"
import { Briefcase, GripVertical, MoreHorizontal } from "lucide-react"
import { Spinner } from "@/components/ui"
import { motion, AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { useJobs, useUpdateJobCompany } from "@/hooks/use-jobs"
import { Button, Badge, Tooltip, Modal, Input, EmptyState } from "@/components/ui"
import { cn, sanitizeCompany, scoreColor, statusLabel } from "@/lib/utils"
import type { Job } from "@/types/api"

const COLUMNS = [
  { key: "found", label: "Discovered", color: "text-blue", dot: "bg-blue" },
  { key: "draft", label: "Drafted", color: "text-accent-sub", dot: "bg-accent" },
  { key: "ready", label: "Ready", color: "text-amber", dot: "bg-amber" },
  { key: "sent", label: "Applied", color: "text-green", dot: "bg-green" },
] as const

type ColumnKey = (typeof COLUMNS)[number]["key"]

export default function OpportunitiesPage() {
  const { data: jobs, isLoading } = useJobs()
  const updateCompany = useUpdateJobCompany()

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

  const buckets: Record<ColumnKey, Job[]> = { found: [], draft: [], ready: [], sent: [] }
  for (const job of jobs || []) {
    buckets[getStatus(job)].push(job)
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
  setOverColumn: (c: ColumnKey | null) => void
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
    </div>
  )
}