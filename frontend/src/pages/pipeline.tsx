import { useEffect, useRef } from "react"
import {
  Rocket, Play, Clock, Search, FileText, Sparkles, Mail, Users, Zap, Terminal, Activity,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { Button, Badge, Skeleton, EmptyState } from "@/components/ui"
import { usePipeline } from "@/hooks/use-pipeline"
import { useJobs } from "@/hooks/use-jobs"
import { cn, sanitizeCompany } from "@/lib/utils"

const agentIcons: Record<string, React.ElementType> = {
  orchestrator: Rocket, web_research: Search, resume_parser: FileText,
  job_application: Sparkles, email_drafting: Mail, apollo: Users,
  outreach: Mail, followup_scheduler: Rocket, fit_scorer: Zap,
}

const agentColors: Record<string, string> = {
  orchestrator: "text-accent", web_research: "text-blue-400", resume_parser: "text-amber",
  job_application: "text-accent", email_drafting: "text-blue-400", apollo: "text-emerald-400",
  outreach: "text-emerald-400", followup_scheduler: "text-accent", fit_scorer: "text-amber",
}

const logStateColor = (step: string) =>
  ["error", "blocked"].includes(step) ? "text-red font-medium" : "text-text-secondary"

export default function PipelinePage() {
  const { events, isRunning, currentMsg, error, start } = usePipeline()
  const { data: jobs, isLoading: jobsLoading } = useJobs()
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [events.length])

  const done = events.some((e) => e.step === "done")
  const hasLogs = events.length > 0
  const doneEvent = events.find((e) => e.step === "done") as any
  const errorEvent = events.find((e) => e.step === "error")
  const results = doneEvent?.results || {}
  const jobsFound = results.jobs_found ?? 0
  const fallbackUsed = !!results.fallback_used
  const failureCat = results.failure_category || (results.errors?.some((er:string)=> er.includes("TAVILY_API_KEY") || er.includes("All AI providers")) ? "provider_unavailable" : null)
  const isProviderFailure = failureCat === "provider_unavailable" || results.status === "blocked"
  const isFailed = !!errorEvent || results.status === "failed" || (failureCat === "discovery_failed" && jobsFound===0)
  const completedEmpty = done && jobsFound === 0 && !isProviderFailure && !isFailed
  const completedWithFallbackEmpty = done && jobsFound===0 && fallbackUsed && !isProviderFailure
  const completedWithFallbackJobs = done && jobsFound>0 && fallbackUsed
  const blocked = events.some((e) => e.step === "blocked") || isProviderFailure

  type PipelineOutcome = "completed_with_jobs" | "completed_empty" | "completed_with_fallback" | "completed_with_fallback_empty" | "provider_unavailable" | "failed"
  let outcome: PipelineOutcome | null = null
  if (done) {
    if (isProviderFailure) outcome = "provider_unavailable"
    else if (isFailed) outcome = "failed"
    else if (fallbackUsed && jobsFound>0) outcome = "completed_with_fallback"
    else if (fallbackUsed && jobsFound===0) outcome = "completed_with_fallback_empty"
    else if (jobsFound>0) outcome = "completed_with_jobs"
    else outcome = "completed_empty"
  }

  return (
    <>
      <Topbar title="Pipeline Orchestration" icon={<Rocket className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>

          {/* Header Controls */}
          <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-text-primary tracking-tight">Autonomous Discovery Pipeline</h2>
              <p className="text-xs text-text-muted">Real-time telemetry, agent streaming log, and match outcomes</p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={isRunning ? "accent" : outcome==="provider_unavailable" ? "red" : outcome==="failed" ? "red" : outcome==="completed_empty" || outcome==="completed_with_fallback_empty" ? "neutral" : outcome==="completed_with_fallback" ? "amber" : done ? "green" : error ? "red" : "neutral"} status={isRunning ? "pulse" : "none"}>
                {isRunning ? "Running" : outcome==="provider_unavailable" ? "Provider Unavailable" : outcome==="failed" ? "Discovery Failed" : outcome==="completed_empty" ? "No New Jobs" : outcome==="completed_with_fallback_empty" ? "No New Jobs (Fallback)" : outcome==="completed_with_fallback" ? "Completed with Fallback" : outcome==="completed_with_jobs" ? "Complete" : done ? "Complete" : error ? "Error" : "Idle"}
              </Badge>
              <Button onClick={start} loading={isRunning} size="sm" className="h-8 text-xs gap-1.5">
                {!isRunning && <Play className="h-3.5 w-3.5" />}
                {isRunning ? "Executing Pipeline…" : "Run Pipeline"}
              </Button>
            </div>
          </div>

          {/* Outcome banners — 5-state UX */}
          {outcome==="completed_empty" && !isRunning && (
            <div className="mb-4 rounded-xl border border-border bg-surface p-4">
              <div className="flex items-start gap-3">
                <div className="grid h-7 w-7 place-items-center rounded-full bg-text-muted/10"><Search className="h-3.5 w-3.5 text-text-muted" /></div>
                <div className="flex-1">
                  <div className="text-xs font-medium text-text-primary">No new jobs found</div>
                  <div className="text-[11px] text-text-muted mt-1">Discovery completed successfully, but this run did not produce any new matching jobs. Existing results may have been filtered as duplicates or failed relevance/quality checks.</div>
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" onClick={start}>Run Pipeline Again</Button>
                    <Button size="sm" variant="ghost" onClick={()=> window.location.href="/discover"}>Paste a JD</Button>
                  </div>
                </div>
              </div>
            </div>
          )}
          {outcome==="completed_with_fallback_empty" && !isRunning && (
            <div className="mb-4 rounded-xl border border-amber/20 bg-amber/[0.04] p-4">
              <div className="flex items-start gap-3">
                <Zap className="h-4 w-4 text-amber mt-0.5 shrink-0" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-text-primary">Discovery completed with fallback — no new jobs found</div>
                  <div className="text-[11px] text-text-muted mt-1">Discovery completed using a fallback AI provider because the primary provider was unavailable. No new jobs were found in this run.</div>
                  <div className="mt-3 flex gap-2">
                    <Button size="sm" onClick={start}>Run Again</Button>
                    <Button size="sm" variant="ghost" onClick={()=> window.location.href="/discover"}>Paste a JD</Button>
                  </div>
                </div>
              </div>
            </div>
          )}
          {outcome==="completed_with_fallback" && !isRunning && (
            <div className="mb-4 rounded-xl border border-amber/20 bg-amber/[0.04] p-4">
              <div className="flex items-start gap-3">
                <Zap className="h-4 w-4 text-amber mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-medium text-text-primary">Discovery completed with fallback</div>
                  <div className="text-[11px] text-text-muted mt-1">Discovery completed using a fallback AI provider because the primary provider was unavailable.</div>
                  <div className="text-[11px] text-text-muted mt-1">{jobsFound} new job{jobsFound===1?"":"s"} found</div>
                </div>
              </div>
            </div>
          )}
          {outcome==="completed_with_jobs" && !isRunning && jobsFound>0 && (
            <div className="mb-4 rounded-xl border border-green/20 bg-green/5 p-4">
              <div className="flex items-start gap-3">
                <div className="grid h-7 w-7 place-items-center rounded-full bg-green/15"><Search className="h-3.5 w-3.5 text-green" /></div>
                <div>
                  <div className="text-xs font-medium text-text-primary">{jobsFound} new job{jobsFound===1?"":"s"} found</div>
                  <div className="text-[11px] text-text-muted mt-1">Discovery completed — results are available in Discover.</div>
                </div>
              </div>
            </div>
          )}
          {outcome==="provider_unavailable" && !isRunning && (
            <div className="mb-4 rounded-xl border border-red/20 bg-red/[0.04] p-4">
              <div className="flex items-start gap-3">
                <Zap className="h-4 w-4 text-red mt-0.5 shrink-0" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-text-primary">Discovery could not complete</div>
                  <div className="text-[11px] text-text-muted mt-1">Required discovery services are unavailable or not configured.</div>
                  <a href="/settings" className="mt-3 inline-flex rounded-md bg-surface border border-border px-3 py-1.5 text-xs hover:bg-surface-hover">Check Settings → API Keys</a>
                </div>
              </div>
            </div>
          )}
          {outcome==="failed" && !isRunning && (
            <div className="mb-4 rounded-xl border border-red/20 bg-red/[0.04] p-4">
              <div className="flex items-start gap-3">
                <Zap className="h-4 w-4 text-red mt-0.5 shrink-0" />
                <div className="flex-1">
                  <div className="text-xs font-medium text-text-primary">Discovery failed</div>
                  <div className="text-[11px] text-text-muted mt-1">Job discovery could not be completed for this run.</div>
                  <Button size="sm" onClick={start} className="mt-3">Retry Pipeline</Button>
                </div>
              </div>
            </div>
          )}

          {/* Blocked banner */}
          {blocked && !isRunning && (
            <div className="mb-4 rounded-xl border border-red/20 bg-red/[0.04] p-4">
              <div className="flex items-start gap-3">
                <Zap className="h-4 w-4 text-red mt-0.5 shrink-0" />
                <div>
                  <div className="text-xs font-medium text-text-primary">Pipeline Blocked</div>
                  <div className="text-[11px] text-text-muted mt-1">
                    {events.find((e) => e.step === "blocked")?.msg || "Resume parsing failed or confidence too low. Please upload a valid resume."}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-6">

            {/* Console Window */}
            <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-black/40 shadow-sm">
              <div className="flex items-center justify-between border-b border-border/80 bg-white/[0.02] px-4 py-3">
                <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-text-muted">
                  <Terminal className="h-3.5 w-3.5 text-accent" />
                  Telemetry Console
                </div>
                <span className="font-mono text-[10px] text-text-faint">pipeline :: live_stream</span>
              </div>

              {!hasLogs && !isRunning ? (
                <EmptyState
                  icon={Rocket}
                  title={error ? "Pipeline Execution Error" : "Ready for Execution"}
                  description={error || 'Click "Run Pipeline" to start autonomous job discovery and candidate intelligence matching.'}
                  className="m-6"
                  compact
                />
              ) : (
                <div ref={logRef} className="h-[440px] flex-1 space-y-1 overflow-y-auto bg-bg-primary/90 p-4 font-mono text-[11px]">
                  <AnimatePresence initial={false}>
                    {events.map((e, i) => {
                      const Icon = agentIcons[e.agent || ""] || Clock
                      return (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -4 }}
                          animate={{ opacity: 1, x: 0 }}
                          className={cn(
                            "flex items-start gap-3 rounded px-2 py-1 transition hover:bg-white/[0.02]",
                            ["error", "blocked"].includes(e.step) && "bg-red/10 border border-red/20"
                          )}
                        >
                          <span className="shrink-0 tabular-nums text-[10px] text-text-faint font-mono w-8 text-right">
                            {e.pct ? String(Math.round(e.pct)).padStart(3, " ") + "%" : "   "}
                          </span>
                          <Icon className={cn("shrink-0 mt-0.5", agentColors[e.agent || ""] || "text-text-faint")} size={12} />
                          <span className={cn("leading-relaxed", logStateColor(e.step))}>{e.msg}</span>
                        </motion.div>
                      )
                    })}
                  </AnimatePresence>
                  {isRunning && (
                    <div className="flex items-center gap-2.5 px-2 py-1.5 text-accent text-xs">
                      <span className="h-3 w-3 animate-spin rounded-full border-2 border-accent border-t-transparent shrink-0" />
                      <span className="animate-pulse">{currentMsg}…</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Pipeline Results & Top Matches */}
            <div className="flex flex-col gap-6">

              {/* Discovery Summary */}
              <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-3">
                <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center justify-between">
                  <span>Discovery Telemetry</span>
                  <Activity className="h-3 w-3 text-text-faint" />
                </div>
                {jobsLoading ? (
                  <Skeleton lines={4} />
                ) : jobs && jobs.length > 0 ? (
                  <div className="space-y-2 pt-1">
                    <ResultRow label="Total Jobs Discovered" value={jobs.length} />
                    <ResultRow label="High Compatibility (≥70%)" value={jobs.filter((j) => (j.fit_score || 0) >= 70).length} color="text-emerald-400" />
                    <ResultRow label="Direct HR Contacts Found" value={jobs.filter((j) => j.hr_email).length} />
                    <ResultRow label="Average Match Score" value={scoreAvg(jobs)} />
                  </div>
                ) : (
                  <p className="text-xs text-text-faint pt-1">No discovery telemetry available yet.</p>
                )}
              </div>

              {/* Top Matches Preview */}
              <div className="flex-1 rounded-xl border border-border bg-bg-secondary p-5 space-y-3">
                <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Top Discovered Matches</div>
                {jobsLoading ? (
                  <Skeleton lines={4} />
                ) : jobs && jobs.length > 0 ? (
                  <div className="space-y-1.5 pt-1">
                    {[...jobs].sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0)).slice(0, 5).map((j) => (
                      <div key={j.id} className="flex items-center justify-between rounded-lg px-3 py-2 border border-border/40 bg-white/[0.01] hover:bg-white/[0.02] transition">
                        <div className="min-w-0 pr-2">
                          <div className="truncate text-xs font-medium text-text-primary">{j.title || "Role"}</div>
                          <div className="truncate text-[11px] text-text-muted">{sanitizeCompany(j.company)}</div>
                        </div>
                        <span className={cn("text-xs font-semibold shrink-0 font-mono", scoreColorClass(j.fit_score || 0))}>
                          {j.fit_score || 0}%
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-text-faint pt-1">No top matches available yet.</p>
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
    <div className="flex items-center justify-between py-1 border-b border-border/40 last:border-0 text-xs">
      <span className="text-text-muted">{label}</span>
      <span className={cn("font-mono font-semibold", color || "text-text-primary")}>{value}</span>
    </div>
  )
}

function scoreAvg(jobs: { fit_score: number | null }[]): string {
  const scores = jobs.map((j) => j.fit_score || 0)
  if (scores.length === 0) return "0%"
  return `${Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)}%`
}

function scoreColorClass(score: number): string {
  if (score >= 70) return "text-emerald-400"
  if (score >= 50) return "text-amber"
  return "text-text-muted"
}