import { useEffect, useRef } from "react"
import { useParams, Link, useNavigate } from "react-router-dom"
import { Rocket, Clock, Search, FileText, Sparkles, Mail, Users, Zap, Terminal, Activity, Play, ExternalLink } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { Button, Badge } from "@/components/ui"
import { usePipeline } from "@/hooks/use-pipeline"
import { useJobs } from "@/hooks/use-jobs"
import { createPipelineStream, fetchPipelineLogs } from "@/api/pipeline"
import { usePipelineStore } from "@/store/pipeline-store"
import { useQuery } from "@tanstack/react-query"
import { cn } from "@/lib/utils"

const agentIcons: Record<string, any> = {
  orchestrator: Rocket, web_research: Search, resume_parser: FileText,
  job_application: Sparkles, email_drafting: Mail, apollo: Users,
  outreach: Mail, followup_scheduler: Rocket, fit_scorer: Zap,
}

export default function PipelineRunPage() {
  const { runId } = useParams()
  const navigate = useNavigate()
  const { events, isRunning, start } = usePipeline()
  const { data: jobs } = useJobs()
  const store = usePipelineStore()
  const logRef = useRef<HTMLDivElement>(null)

  // Load authoritative persisted state on mount/refresh
  const { data: persisted } = useQuery({
    queryKey: ["pipeline-run", runId],
    queryFn: () => fetchPipelineLogs(runId!),
    enabled: !!runId,
  })

  useEffect(() => {
    if (persisted && Array.isArray(persisted) && persisted.length > 0) {
      // Hydrate store from persisted if store is empty (refresh case)
      if (store.events.length === 0) {
        persisted.forEach((ev: any) => store.addEvent(ev))
      }
    }
  }, [persisted])

  // Establish SSE for live updates
  useEffect(() => {
    if (!runId) return
    const es = createPipelineStream(runId)
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data)
        store.addEvent(ev)
      } catch {}
    }
    es.onerror = () => {
      // retain state, indicate reconnecting
      es.close()
    }
    return () => es.close()
  }, [runId])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [store.events.length])

  const done = store.events.some(e => e.step === "done")
  const blocked = store.events.some(e => e.step === "blocked")
  const error = store.events.some(e => e.step === "error")

  return (
    <>
      <Topbar title="Pipeline Run" icon={<Rocket className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">
        <div className="flex items-center gap-2 text-xs">
          <Link to="/" className="text-text-muted hover:text-text-primary">← Dashboard</Link>
          <span className="text-text-faint">/</span>
          <span className="font-mono text-text-primary">RUN-{runId}</span>
          <Badge variant={isRunning ? "accent" : blocked ? "red" : done ? "green" : error ? "red" : "neutral"} status={isRunning ? "pulse" : "none"}>
            {isRunning ? "RUNNING" : blocked ? "BLOCKED" : done ? "COMPLETED" : error ? "FAILED" : "IDLE"}
          </Badge>
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="text-[11px] font-medium uppercase tracking-wider text-text-faint">Pipeline Progress</div>
          <div className="mt-3 space-y-2">
            {[
              { key: "discover", label: "Job Discovery", done: store.events.some(e => e.step === "discover_done"), active: store.currentStep === "discover" },
              { key: "analyze", label: "Job Analysis", done: store.events.some(e => e.step === "parse_done"), active: store.currentStep === "parse_done" },
              { key: "match", label: "Candidate Matching", done: store.events.some(e => e.step === "score_done"), active: store.currentStep === "score_done" },
              { key: "rank", label: "Priority Ranking", done: store.events.some(e => e.step === "tailor_done"), active: store.currentStep === "tailor_done" },
              { key: "save", label: "Dashboard Update", done, active: false },
            ].map(s => (
              <div key={s.key} className="flex items-center gap-2 text-xs">
                <span className={s.done ? "text-green" : s.active ? "text-accent" : "text-text-faint"}>{s.done ? "✓" : s.active ? "●" : "○"}</span>
                <span className={s.done ? "text-text-primary" : s.active ? "text-accent" : "text-text-muted"}>{s.label}</span>
                <span className="ml-auto text-[10px] text-text-faint">{s.done ? "Done" : s.active ? "Processing..." : "Waiting"}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-black/40">
          <div className="flex items-center justify-between border-b border-border/80 bg-white/[0.02] px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-text-muted">
              <Terminal className="h-3.5 w-3.5 text-accent" /> Activity
            </div>
            <span className="font-mono text-[10px] text-text-faint">live</span>
          </div>
          <div ref={logRef} className="h-[300px] overflow-y-auto p-4 font-mono text-[11px] space-y-1">
            {store.events.map((e, i) => {
              const Icon = agentIcons[e.agent || ""] || Clock
              return (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-8 text-right tabular-nums text-[10px] text-text-faint">{e.pct ? `${Math.round(e.pct)}%` : ""}</span>
                  <Icon size={12} className="mt-0.5 text-text-faint" />
                  <span className="text-text-secondary">{e.msg}</span>
                </div>
              )
            })}
            {isRunning && <div className="text-accent text-xs animate-pulse">{store.currentMsg}…</div>}
            {!isRunning && done && <div className="text-green text-xs">✓ Pipeline completed — {jobs?.length || 0} jobs</div>}
          </div>
        </div>

        {done && (
          <div className="flex gap-2">
            <Link to="/discover"><Button size="sm">View Opportunities</Button></Link>
            <Link to="/"><Button size="sm" variant="ghost">Back to Dashboard</Button></Link>
          </div>
        )}
        {blocked && (
          <div className="rounded-xl border border-red/20 bg-red/[0.04] p-4 text-xs">
            Pipeline blocked — check resume. <Link to="/resume" className="text-accent underline">Resume Studio</Link>
          </div>
        )}
      </div>
    </>
  )
}
