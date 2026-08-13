import { Home, Briefcase, Send, Calendar, Target, Search, RefreshCw, Upload, Eye, Mail, TrendingUp, Check } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { StatCard } from "@/components/dashboard/stat-card"
import { useDashboard } from "@/hooks/use-dashboard"
import { usePipeline } from "@/hooks/use-pipeline"
import { cn } from "@/lib/utils"

export default function DashboardPage() {
  const { analytics, status, resume, email, isLoading } = useDashboard()
  const { start } = usePipeline()
  const navigate = useNavigate()

  const totalJobs = analytics?.total_jobs || 0
  const drafted = analytics?.applications_drafted || 0
  const emailed = analytics?.emails_sent || 0
  const strongMatches = analytics?.strong_matches || 0
  const recruiters = analytics?.recruiters_found || status?.recruiters_count || 0

  const h = new Date().getHours()
  const greet = h < 12 ? "Good Morning" : h < 17 ? "Good Afternoon" : "Good Evening"
  const name = resume?.uploaded && resume?.parsed ? (resume.parsed as any)?.name?.split(" ")[0] || "there" : "there"

  const onboarded = resume?.uploaded && resume?.parsed && (totalJobs > 0 || recruiters > 0)

  if (isLoading) {
    return (
      <>
        <Topbar title="Home" icon={<Home className="h-5 w-5" />} />
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 w-full animate-shimmer rounded-lg" />
            ))}
          </div>
        </div>
      </>
    )
  }

  // ── Onboarding Flow ──
  if (!onboarded) {
    const steps = [
      { key: "resume", label: "Upload your resume", done: !!resume?.uploaded, icon: Upload, desc: "Let us know who you are", action: () => navigate("/resume"), btn: "Upload" },
      { key: "parse", label: "Parse your resume", done: !!resume?.parsed, icon: Eye, desc: "Extract skills and experience", action: () => navigate("/resume"), btn: "View Resume" },
      { key: "discover", label: "Run your first discovery", done: totalJobs > 0, icon: Search, desc: "Find matching opportunities", action: () => start(), btn: "Run Discovery" },
      { key: "review", label: "Review matching jobs", done: totalJobs >= 3, icon: Eye, desc: "Pick the best opportunities", action: () => navigate("/discover"), btn: "Review Jobs" },
      { key: "email", label: "Connect your email", done: !!email?.configured, icon: Mail, desc: "Send applications directly", action: () => navigate("/settings"), btn: "Connect" },
    ]
    const doneCount = steps.filter((s) => s.done).length
    const nextStep = steps.find((s) => !s.done)

    return (
      <>
        <Topbar title="Home" icon={<Home className="h-5 w-5" />} />
        <div className="flex-1 overflow-y-auto p-6">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <h1 className="text-lg font-semibold">
              {greet}, {name} 👋
            </h1>
            <p className="mb-6 text-[13px] text-text-muted">Let's get your job search set up in 5 steps.</p>

            <div className="max-w-[600px] rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-[13px] font-semibold">Setup Progress</span>
                <span className="font-mono text-[11px] text-text-muted">{doneCount}/5</span>
              </div>
              <div className="mb-3 h-1 overflow-hidden rounded-full bg-bg-tertiary">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-accent to-accent-sub"
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.round((doneCount / 5) * 100)}%` }}
                  transition={{ duration: 0.6 }}
                />
              </div>

              <div className="space-y-0">
                {steps.map((step, i) => {
                  const isNext = step === nextStep
                  return (
                    <div
                      key={step.key}
                      className={cn(
                        "flex items-center gap-3.5 py-2.5",
                        i < steps.length - 1 && "border-b border-border",
                        isNext ? "opacity-100" : step.done ? "opacity-50" : "opacity-30"
                      )}
                    >
                      <div
                        className={cn(
                          "grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold",
                          step.done
                            ? "bg-green-bg text-green"
                            : isNext
                              ? "bg-accent-bg text-accent-sub"
                              : "bg-bg-tertiary text-text-muted"
                        )}
                      >
                        {step.done ? <Check className="h-4 w-4" /> : i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className={cn("text-[13px] font-semibold", step.done ? "text-green" : isNext ? "text-text-primary" : "text-text-muted")}>
                          {step.label}
                        </div>
                        <div className="text-[11px] text-text-muted">{step.done ? "Completed" : step.desc}</div>
                      </div>
                      {!step.done && isNext ? (
                        <button
                          onClick={step.action}
                          className="shrink-0 rounded-md bg-gradient-to-br from-accent to-teal-600 px-3.5 py-1.5 text-[12px] font-semibold text-white shadow-[0_3px_12px] shadow-accent-glow transition hover:-translate-y-0.5"
                        >
                          {step.btn}
                        </button>
                      ) : step.done ? (
                        <span className="text-[11px] text-green">Done</span>
                      ) : (
                        <span className="text-[11px] text-text-muted">Pending</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </motion.div>
        </div>
      </>
    )
  }

  // ── Full Dashboard ──
  const pipelineSteps = [
    { label: "Resume Uploaded", ok: !!resume?.uploaded },
    { label: "Resume Parsed", ok: !!resume?.parsed },
    { label: "Jobs Discovered", ok: totalJobs > 0, val: totalJobs },
    { label: "Strong Matches", ok: strongMatches > 0, val: strongMatches },
    { label: "Recruiters Found", ok: recruiters > 0, val: recruiters },
    { label: "Applications Ready", ok: drafted > 0, val: drafted },
  ]
  const doneSteps = pipelineSteps.filter((s) => s.ok).length
  const pct = Math.round((doneSteps / pipelineSteps.length) * 100)

  let action = "Review opportunities and tailor your resume"
  if (drafted > 0) action = `${drafted} applications ready to send`
  if (!email?.configured) action += " — connect email to send"

  return (
    <>
      <Topbar title="Home" icon={<Home className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          {/* Header */}
          <div className="mb-5 flex items-start justify-between">
            <div>
              <h1 className="text-lg font-semibold">{greet}, {name} 👋</h1>
              <p className="text-[13px] text-text-muted">
                Your search is active — {totalJobs} jobs found, {drafted} ready to send.
              </p>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-text-muted">
              <div className="h-1.5 w-1.5 rounded-full bg-green" />
              Pipeline {status?.resume_parsed ? "Active" : "Needs Setup"}
            </div>
          </div>

          {/* KPIs */}
          <div className="mb-5 grid grid-cols-4 gap-4">
            <StatCard label="Jobs Found" value={totalJobs} sub="Across all sources" icon={Briefcase} />
            <StatCard label="Applied" value={emailed} sub="Applications sent" icon={Send} />
            <StatCard label="This Week" value={analytics?.applications_by_source ? Object.values(analytics.applications_by_source).reduce((a: number, b: number) => a + b, 0) : 0} sub="New applications" icon={Calendar} />
            <StatCard label="Response Rate" value={`${analytics?.company_response_rate || 0}%`} sub="Interview conversion" icon={Target} />
          </div>

          {/* Action + Progress */}
          <div className="mb-5 grid grid-cols-2 gap-4">
            {/* Next Action */}
            <div className="rounded-lg border border-accent/20 bg-accent/[0.02] p-5">
              <div className="mb-3 flex items-center gap-2">
                <Target className="h-4 w-4 text-accent-sub" />
                <span className="text-[12px] font-semibold text-accent-sub">Next Action</span>
              </div>
              <p className="text-sm font-medium text-text-primary">{action}</p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => navigate("/discover")}
                  className="flex items-center gap-1.5 rounded-md bg-gradient-to-br from-accent to-teal-600 px-3.5 py-1.5 text-[12px] font-semibold text-white shadow-[0_3px_12px] shadow-accent-glow"
                >
                  <Search className="h-3.5 w-3.5" />
                  View Jobs
                </button>
                <button
                  onClick={start}
                  className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3.5 py-1.5 text-[12px] font-semibold text-text-primary transition hover:bg-surface-hover"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Refresh
                </button>
              </div>
            </div>

            {/* Progress */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-text-muted" />
                <span className="text-[12px] font-semibold uppercase tracking-wider text-text-muted">Progress</span>
              </div>
              <div className="mb-2.5 flex items-center gap-2">
                <div className="h-1 flex-1 overflow-hidden rounded-full bg-bg-tertiary">
                  <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent-sub" style={{ width: `${pct}%` }} />
                </div>
                <span className="font-mono text-[10px] text-text-muted">{doneSteps}/{pipelineSteps.length}</span>
              </div>
              <div className="space-y-1">
                {pipelineSteps.map((step) => (
                  <div key={step.label} className="flex items-center gap-2.5">
                    <div className={cn("grid h-5 w-5 place-items-center rounded-full text-[9px] font-bold", step.ok ? "bg-green-bg text-green" : "bg-bg-tertiary text-text-muted")}>
                      {step.ok ? "✓" : "·"}
                    </div>
                    <span className="flex-1 text-[12px] text-text-secondary">{step.label}</span>
                    {step.val !== undefined && <span className="font-mono text-[10px] text-text-muted">{step.val}</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="mb-2 text-[12px] font-semibold uppercase tracking-wider text-text-muted">Recent Activity</div>
          <div className="rounded-lg border border-border bg-surface p-4">
            {totalJobs === 0 ? (
              <p className="text-center text-[13px] text-text-muted">No activity yet — run a discovery to get started</p>
            ) : (
              <div className="space-y-2">
                {resume?.parsed && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-5 w-5 place-items-center rounded-full bg-green-bg text-[9px] font-bold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">Resume parsed with {analytics?.avg_score || 0}% quality score</span>
                    <span className="text-[10px] text-text-muted">Today</span>
                  </div>
                )}
                {totalJobs > 0 && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-5 w-5 place-items-center rounded-full bg-green-bg text-[9px] font-bold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">Discovered {totalJobs} matching opportunities</span>
                    <span className="text-[10px] text-text-muted">Today</span>
                  </div>
                )}
                {recruiters > 0 && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-5 w-5 place-items-center rounded-full bg-green-bg text-[9px] font-bold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">Found {recruiters} recruiters</span>
                    <span className="text-[10px] text-text-muted">Today</span>
                  </div>
                )}
                {drafted > 0 && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-5 w-5 place-items-center rounded-full bg-green-bg text-[9px] font-bold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">{drafted} applications ready</span>
                    <span className="text-[10px] text-text-muted">Today</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </>
  )
}
