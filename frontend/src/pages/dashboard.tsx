import { Home, Briefcase, Send, Calendar, Target, Search, RefreshCw, Upload, Eye, Mail, TrendingUp, Check, BarChart3, Lightbulb } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { StatCard } from "@/components/dashboard/stat-card"
import { useDashboard, useOutcomeOverview, useOutcomeInsights } from "@/hooks/use-dashboard"
import { usePipeline } from "@/hooks/use-pipeline"
import { useApplications } from "@/hooks/use-applications"
import { useJobs } from "@/hooks/use-jobs"
import { cn, sanitizeCompany } from "@/lib/utils"
import { getNextActionForApplication } from "@/lib/next-action"
import { PriorityBadge } from "@/components/ui/priority-badge"
import { Link } from "react-router-dom"

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

  const outcomeOverview = useOutcomeOverview()
  const outcomeInsights = useOutcomeInsights()

  if (isLoading) {
    return (
      <>
        <Topbar title="Home" icon={<Home className="h-4 w-4" />} />
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 w-full animate-shimmer rounded-xl" />
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
        <Topbar title="Home" icon={<Home className="h-4 w-4" />} />
        <div className="flex-1 overflow-y-auto p-6">
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
            <h1 className="text-[18px] font-semibold tracking-tight">
              {greet}, {name}
            </h1>
            <p className="mb-6 text-[13px] text-text-muted">Let's get your job search set up in 5 steps.</p>

            <div className="max-w-[560px] rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 flex items-center justify-between">
                <span className="text-[13px] font-medium">Setup Progress</span>
                <span className="font-mono text-[11px] text-text-faint">{doneCount}/5</span>
              </div>
              <div className="mb-4 h-[3px] overflow-hidden rounded-full bg-white/[0.04]">
                <motion.div
                  className="h-full rounded-full bg-accent/70"
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
                        "flex items-center gap-3.5 py-3",
                        i < steps.length - 1 && "border-b border-border",
                        isNext ? "opacity-100" : step.done ? "opacity-40" : "opacity-20"
                      )}
                    >
                      <div
                        className={cn(
                          "grid h-8 w-8 shrink-0 place-items-center rounded-full text-[12px] font-semibold",
                          step.done
                            ? "bg-green/[0.08] text-green"
                            : isNext
                              ? "bg-accent/[0.08] text-accent-sub"
                              : "bg-white/[0.04] text-text-faint"
                        )}
                      >
                        {step.done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className={cn("text-[13px] font-medium", step.done ? "text-green" : isNext ? "text-text-primary" : "text-text-faint")}>
                          {step.label}
                        </div>
                        <div className="text-[11px] text-text-muted">{step.done ? "Completed" : step.desc}</div>
                      </div>
                      {!step.done && isNext ? (
                        <button
                          onClick={step.action}
                          className="shrink-0 rounded-lg bg-accent/90 px-3.5 py-1.5 text-[12px] font-medium text-white shadow-sm shadow-accent/10 transition-all hover:bg-accent hover:shadow-md hover:shadow-accent/15"
                        >
                          {step.btn}
                        </button>
                      ) : step.done ? (
                        <span className="text-[11px] text-green/60">Done</span>
                      ) : (
                        <span className="text-[11px] text-text-faint">Pending</span>
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
      <Topbar title="Home" icon={<Home className="h-4 w-4" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          {/* Header */}
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h1 className="text-[18px] font-semibold tracking-tight">{greet}, {name}</h1>
              <p className="mt-0.5 text-[13px] text-text-muted">
                {totalJobs} jobs found · {drafted} ready to send
              </p>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-text-faint">
              <div className="h-[5px] w-[5px] rounded-full bg-green/60" />
              Pipeline {status?.resume_parsed ? "Active" : "Needs Setup"}
            </div>
          </div>

          {/* KPIs */}
          <div className="mb-6 grid grid-cols-4 gap-3">
            <StatCard label="Jobs Found" value={totalJobs} sub="Across all sources" icon={Briefcase} />
            <StatCard label="Applied" value={emailed} sub="Applications sent" icon={Send} />
            <StatCard label="This Week" value={analytics?.applications_by_source ? Object.values(analytics.applications_by_source).reduce((a: number, b: number) => a + b, 0) : 0} sub="New applications" icon={Calendar} />
            <StatCard label="Response Rate" value={`${analytics?.company_response_rate || 0}%`} sub="Interview conversion" icon={Target} />
          </div>

          {/* Action + Progress */}
          <div className="mb-6 grid grid-cols-2 gap-3">
            {/* Next Action */}
            <div className="rounded-xl border border-accent/[0.08] bg-accent/[0.02] p-5">
              <div className="mb-3 flex items-center gap-2">
                <Target className="h-3.5 w-3.5 text-accent-sub/70" />
                <span className="text-[11px] font-medium uppercase tracking-wider text-accent-sub/70">Next Action</span>
              </div>
              <p className="text-[14px] font-medium text-text-primary">{action}</p>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => navigate("/discover")}
                  className="flex items-center gap-1.5 rounded-lg bg-accent/90 px-3.5 py-1.5 text-[12px] font-medium text-white shadow-sm shadow-accent/10 transition hover:bg-accent"
                >
                  <Search className="h-3 w-3" />
                  View Jobs
                </button>
                <button
                  onClick={start}
                  className="flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.02] px-3.5 py-1.5 text-[12px] font-medium text-text-primary transition hover:bg-white/[0.04]"
                >
                  <RefreshCw className="h-3 w-3" />
                  Refresh
                </button>
              </div>
            </div>

            {/* Progress */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-3 flex items-center gap-2">
                <TrendingUp className="h-3.5 w-3.5 text-text-faint" />
                <span className="text-[11px] font-medium uppercase tracking-wider text-text-faint">Progress</span>
              </div>
              <div className="mb-3 flex items-center gap-2">
                <div className="h-[3px] flex-1 overflow-hidden rounded-full bg-white/[0.04]">
                  <div className="h-full rounded-full bg-accent/60" style={{ width: `${pct}%` }} />
                </div>
                <span className="font-mono text-[10px] text-text-faint">{doneSteps}/{pipelineSteps.length}</span>
              </div>
              <div className="space-y-1.5">
                {pipelineSteps.map((step) => (
                  <div key={step.label} className="flex items-center gap-2.5">
                    <div className={cn(
                      "grid h-[18px] w-[18px] place-items-center rounded-full text-[8px] font-semibold",
                      step.ok ? "bg-green/[0.08] text-green" : "bg-white/[0.04] text-text-faint"
                    )}>
                      {step.ok ? "✓" : "·"}
                    </div>
                    <span className="flex-1 text-[12px] text-text-secondary">{step.label}</span>
                    {step.val !== undefined && <span className="font-mono text-[10px] text-text-faint">{step.val}</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── Outcome / Learning Section (Phase 12) ── */}
          <OutcomeSection overview={outcomeOverview} insights={outcomeInsights} />

          {/* ── Active Work (Phase 14) ── */}
          <ActiveWorkSection />

          {/* Recent Activity */}
          <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-faint">Recent Activity</div>
          <div className="rounded-xl border border-border bg-surface p-5">
            {totalJobs === 0 ? (
              <p className="text-center text-[13px] text-text-muted">No activity yet — run a discovery to get started</p>
            ) : (
              <div className="space-y-2.5">
                {resume?.parsed && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-[18px] w-[18px] place-items-center rounded-full bg-green/[0.08] text-[8px] font-semibold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">Resume parsed with {analytics?.avg_score || 0}% quality score</span>
                    <span className="text-[10px] text-text-faint">Today</span>
                  </div>
                )}
                {totalJobs > 0 && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-[18px] w-[18px] place-items-center rounded-full bg-green/[0.08] text-[8px] font-semibold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">Discovered {totalJobs} matching opportunities</span>
                    <span className="text-[10px] text-text-faint">Today</span>
                  </div>
                )}
                {recruiters > 0 && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-[18px] w-[18px] place-items-center rounded-full bg-green/[0.08] text-[8px] font-semibold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">Found {recruiters} recruiters</span>
                    <span className="text-[10px] text-text-faint">Today</span>
                  </div>
                )}
                {drafted > 0 && (
                  <div className="flex items-center gap-2.5">
                    <div className="grid h-[18px] w-[18px] place-items-center rounded-full bg-green/[0.08] text-[8px] font-semibold text-green">✓</div>
                    <span className="flex-1 text-[12px] text-text-secondary">{drafted} applications ready</span>
                    <span className="text-[10px] text-text-faint">Today</span>
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

function Rate({ num, den }: { num: number | null | undefined; den: number | null | undefined }) {
  if (!den || den === 0 || num == null) return <span className="text-text-faint">Not enough data yet</span>
  const pct = Math.round((num / den) * 100)
  return <span className="font-mono text-text-primary">{pct}%</span>
}

function OutcomeSection({
  overview,
  insights,
}: {
  overview: ReturnType<typeof useOutcomeOverview>
  insights: ReturnType<typeof useOutcomeInsights>
}) {
  const funnel = overview.data?.funnel
  const loading = overview.isLoading
  const ins = insights.data

  if (loading) {
    return (
      <div className="mb-6">
        <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-faint">Outcome</div>
        <div className="h-24 w-full animate-shimmer rounded-xl" />
      </div>
    )
  }

  if (!funnel || funnel.applications_started === 0) {
    return (
      <div className="mb-6">
        <div className="mb-2 text-[11px] font-medium uppercase tracking-wider text-text-faint">Outcome</div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <p className="text-center text-[13px] text-text-muted">Not enough data yet</p>
        </div>
      </div>
    )
  }

  const rateRows = [
    { label: "Apply → Screening", num: funnel.application_to_screening_rate, den: funnel.applications_submitted },
    { label: "Apply → Interview", num: funnel.application_to_interview_rate, den: funnel.applications_submitted },
    { label: "Interview → Offer", num: funnel.final_to_offer_rate, den: funnel.interview_count },
    { label: "Offer → Accepted", num: funnel.offer_to_acceptance_rate, den: funnel.offer_count },
  ]

  const topInsights = (ins?.insights || []).filter((i) => i.confidence === "OBSERVED").slice(0, 2)

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-text-faint">
        <BarChart3 className="h-3 w-3" />
        Outcome
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-3 text-[12px] font-medium text-text-secondary">Funnel</div>
          <div className="space-y-2">
            {[
              { label: "Applications Started", val: funnel.applications_started },
              { label: "Applications Submitted", val: funnel.applications_submitted },
              { label: "Screening", val: funnel.screening_count },
              { label: "Interview", val: funnel.interview_count },
              { label: "Offer", val: funnel.offer_count },
              { label: "Accepted", val: funnel.accepted_count },
            ].map((r) => (
              <div key={r.label} className="flex items-center justify-between text-[12px]">
                <span className="text-text-muted">{r.label}</span>
                <span className="font-mono text-text-primary">{r.val}</span>
              </div>
            ))}
          </div>
          <div className="my-3 border-t border-border" />
          <div className="mb-2 text-[11px] font-medium text-text-faint">Conversion Rates</div>
          <div className="space-y-2">
            {rateRows.map((r) => (
              <div key={r.label} className="flex items-center justify-between text-[12px]">
                <span className="text-text-muted">{r.label}</span>
                <Rate num={r.num} den={r.den} />
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-3 flex items-center gap-1.5 text-[12px] font-medium text-text-secondary">
            <Lightbulb className="h-3.5 w-3.5 opacity-50" />
            Insights
          </div>
          {ins?.status === "INSUFFICIENT_DATA" || topInsights.length === 0 ? (
            <p className="text-[13px] text-text-muted">Not enough data yet</p>
          ) : (
            <div className="space-y-3">
              {topInsights.map((i, idx) => (
                <div key={idx} className="rounded-lg bg-white/[0.02] p-3">
                  <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-text-faint">
                    {i.dimension === "application_priority" ? `Priority: ${i.segment}` : `Source: ${i.segment}`}
                  </div>
                  <div className="space-y-1 text-[12px]">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Applications</span>
                      <span className="font-mono text-text-primary">{i.applications}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Interviews</span>
                      <span className="font-mono text-text-primary">{i.interviews}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Interview Rate</span>
                      <span className="font-mono text-text-primary">
                        {i.interview_rate != null ? `${Math.round(i.interview_rate * 100)}%` : "N/A"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ActiveWorkSection() {
  const { data: apps } = useApplications()
  const { data: jobs } = useJobs()
  const needingReview = jobs?.filter((j: any) => !apps?.some((a: any) => a.job_id === j.id)).slice(0, 3) || []
  const needingAction = apps?.filter((a: any) => ["PREPARING", "READY_TO_APPLY", "OFFER"].includes(a.current_state)).slice(0, 3) || []
  const recentOutcomes = apps?.filter((a: any) => a.current_state === "CLOSED").slice(0, 2) || []

  if (!apps && !jobs) return null
  if (needingReview.length === 0 && needingAction.length === 0 && recentOutcomes.length === 0) return null

  return (
    <div className="mb-6">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-[11px] font-medium uppercase tracking-wider text-text-faint">Today&apos;s priorities</h2>
        <span className="h-px flex-1 bg-border" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-3 text-[13px] font-medium text-text-primary">Jobs to review</div>
          {needingReview.length === 0 ? <p className="text-[12px] text-text-muted">No jobs needing review — run discovery</p> : needingReview.map((j: any, i:number) => (
            <Link key={j.id} to={`/jobs/${j.id}`} className="flex items-center justify-between gap-2 py-2 text-[12px] hover:bg-white/[0.02] -mx-2 px-2 rounded-lg transition">
              <div className="flex items-center gap-2 min-w-0">
                <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-accent/[0.08] text-[10px] font-semibold text-accent-sub">{i+1}</span>
                <span className="truncate text-accent-sub">{j.title}</span>
                <span className="text-text-faint truncate">· {sanitizeCompany(j.company)}</span>
              </div>
              <PriorityBadge tier={j.priority_tier || (j.fit_score >= 80 ? "HOT" : j.fit_score >= 65 ? "WARM" : "REVIEW")} size="sm" className="shrink-0" />
            </Link>
          ))}
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-3 text-[13px] font-medium text-text-primary">Next actions</div>
          {needingAction.length === 0 ? <p className="text-[12px] text-text-muted">No action needed — check back after discovery</p> : needingAction.map((a: any) => {
            const next = getNextActionForApplication(a)
            return <Link key={a.id} to={next.to} className="flex items-center justify-between py-2 -mx-2 px-2 rounded-lg hover:bg-white/[0.02] transition">
              <span className="text-[12px] text-text-primary">{a.job_title_snapshot || `App #${a.id}`}</span>
              <span className="rounded-md bg-accent/[0.08] px-2 py-0.5 text-[10px] font-medium text-accent-sub">{next.label}</span>
            </Link>
          })}
        </div>
        <div className="rounded-xl border border-border bg-surface p-5">
          <div className="mb-3 text-[13px] font-medium text-text-primary">Learning</div>
          {recentOutcomes.length === 0 ? <p className="text-[12px] text-text-muted">Complete an application to see learning</p> : recentOutcomes.map((a: any) => (
            <div key={a.id} className="py-2 text-[12px] border-b border-border last:border-0 -mx-2 px-2">
              <div className="font-medium text-text-primary">{a.job_title_snapshot}</div>
              <div className="text-[11px] text-text-faint">{a.final_outcome || "CLOSED"} · {new Date(a.last_state_change_at || a.created_at).toLocaleDateString()}</div>
            </div>
          ))}
          <Link to="/analytics" className="mt-3 inline-flex text-[11px] font-medium text-accent-sub/80 hover:text-accent-sub transition-colors">View Outcome Analytics →</Link>
        </div>
      </div>
    </div>
  )
}
