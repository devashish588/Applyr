import { useEffect, useRef } from "react"
import {
  Rocket, Play, Clock, Search, FileText, Sparkles, Mail, Users, Zap,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { Button, Badge, Skeleton, EmptyState } from "@/components/ui"
import { usePipeline } from "@/hooks/use-pipeline"
import { useJobs } from "@/hooks/use-jobs"
import { cn } from "@/lib/utils"

const agentIcons: Record<string, React.ElementType> = {
  orchestrator: Rocket, web_research: Search, resume_parser: FileText,
  job_application: Sparkles, email_drafting: Mail, apollo: Users,
  outreach: Mail, followup_scheduler: Rocket, fit_scorer: Zap,
}

const agentColors: Record<string, string> = {
  orchestrator: "text-accent-sub", web_research: "text-blue", resume_parser: "text-amber",
  job_application: "text-accent-sub", email_drafting: "text-blue", apollo: "text-green",
  outreach: "text-green", followup_scheduler: "text-accent-sub", fit_scorer: "text-amber",
}

const logStateColor = (step: string) =>
  ["error", "blocked"].includes(step) ? "text-red" : "text-text-secondary"

export default function PipelinePage() {
  const { events, isRunning, currentMsg, error, start } = usePipeline()
  const { data: jobs, isLoading: jobsLoading } = useJobs()
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [events.length])

  const done = events.some((e) => e.step === "done")
  const hasLogs = events.length > 0

  return (
    <>
      <Topbar title="Pipeline" icon={<Rocket className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          {/* Header */}
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h2 className="text-[15px] font-semibold">Run Discovery</h2>
              <p className="text-[12px] text-text-muted">Live pipeline execution and results</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={isRunning ? "accent" : done ? "green" : error ? "red" : "neutral"} status={isRunning ? "pulse" : "none"}>
                {isRunning ? "Running" : done ? "Complete" : error ? "Error" : "Idle"}
              </Badge>
              <Button onClick={start} loading={isRunning} size="sm">
                {!isRunning && <Play className="h-3.5 w-3.5" />}
                {isRunning ? "Running…" : "Run Now"}
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-[1.6fr_1fr] gap-4">
            {/* Console */}
            <div className="flex flex-col overflow-hidden rounded-lg border border-border bg-surface">
              <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_6px] shadow-accent" />
                  Console
                </div>
                <span className="font-mono text-[10px] text-text-muted">pipeline :: stream</span>
              </div>

              {!hasLogs && !isRunning ? (
                <EmptyState
                  icon={Rocket}
                  title={error ? "Run failed" : "No runs yet"}
                  description={error || 'Hit "Run Now" to execute the full discovery pipeline.'}
                  className="m-4"
                  compact
                />
              ) : (
                <div ref={logRef} className="max-h-[420px] flex-1 space-y-0.5 overflow-y-auto bg-bg p-3 font-mono text-[11px]">
                  <AnimatePresence initial={false}>
                    {events.map((e, i) => {
                      const Icon = agentIcons[e.agent || ""] || Clock
                      return (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -6 }}
                          animate={{ opacity: 1, x: 0 }}
                          className={cn(
                            "flex items-start gap-2.5 rounded px-1.5 py-[3px]",
                            ["error", "blocked"].includes(e.step) && "bg-red-bg/40"
                          )}
                        >
                          <span className="shrink-0 tabular-nums text-[10px] text-text-muted">
                            {e.pct ? String(Math.round(e.pct)).padStart(3, " ") + "%" : "   "}
                          </span>
                          <Icon className={cn("shrink-0", agentColors[e.agent || ""] || "text-text-muted")} size={11} />
                          <span className={logStateColor(e.step)}>{e.msg}</span>
                        </motion.div>
                      )
                    })}
                  </AnimatePresence>
                  {isRunning && (
                    <div className="flex items-center gap-2 px-1.5 py-[3px] text-accent-sub">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent-sub border-t-transparent" />
                      <span className="animate-blink">{currentMsg}…</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Results */}
            <div className="flex flex-col gap-4">
              <div className="rounded-lg border border-border bg-surface p-4">
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Discovery Results</div>
                {jobsLoading ? (
                  <Skeleton lines={4} />
                ) : jobs && jobs.length > 0 ? (
                  <div className="space-y-1">
                    <ResultRow label="Jobs discovered" value={jobs.length} />
                    <ResultRow label="Best matches (≥70%)" value={jobs.filter((j) => (j.fit_score || 0) >= 70).length} color="text-green" />
                    <ResultRow label="With contact" value={jobs.filter((j) => j.hr_email).length} />
                    <ResultRow label="Avg fit score" value={scoreAvg(jobs)} />
                  </div>
                ) : (
                  <p className="text-[12px] text-text-muted">No results yet. Run the pipeline.</p>
                )}
              </div>

              <div className="flex-1 rounded-lg border border-border bg-surface p-4">
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Top Matches</div>
                {jobsLoading ? (
                  <Skeleton lines={3} />
                ) : jobs && jobs.length > 0 ? (
                  <div className="space-y-0.5">
                    {[...jobs].sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0)).slice(0, 5).map((j) => (
                      <div key={j.id} className="flex items-center justify-between rounded px-2 py-1.5 transition hover:bg-surface-hover">
                        <div className="min-w-0">
                          <div className="truncate text-[12px] font-medium text-text-primary">{j.title || "Role"}</div>
                          <div className="truncate text-[11px] text-text-muted">{j.company || "—"}</div>
                        </div>
                        <span className={cn("ml-2 text-[12px] font-bold", scoreColorClass(j.fit_score || 0))}>
                          {j.fit_score || 0}%
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[12px] text-text-muted">No matches yet.</p>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </>
  )
}

function ResultRow({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[12px] text-text-secondary">{label}</span>
      <span className={cn("font-mono text-[12px] font-semibold", color || "text-text-primary")}>{value}</span>
    </div>
  )
}

function scoreAvg(jobs: { fit_score: number | null }[]): string {
  const scores = jobs.map((j) => j.fit_score || 0)
  if (scores.length === 0) return "0%"
  return `${Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)}%`
}

function scoreColorClass(score: number): string {
  if (score >= 70) return "text-green"
  if (score >= 50) return "text-amber"
  return "text-text-muted"
}