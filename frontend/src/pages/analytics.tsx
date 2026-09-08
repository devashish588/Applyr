import { BarChart3, Briefcase, Send, MessageSquare, Trophy, Filter, TrendingUp, Users, Mail, Clock, AlertCircle, Info } from "lucide-react"
import { motion } from "framer-motion"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from "recharts"
import { Topbar } from "@/components/layout/topbar"
import { Badge } from "@/components/ui"
import { useAnalytics, useOutcomeOverview, useOutcomeInsights } from "@/hooks/use-dashboard"
import type { Analytics } from "@/types/api"
import { Link } from "react-router-dom"

// Semantic tokens for analytics
const SEMANTIC = {
  applications: { color: "#5B8CFF", bg: "rgba(91,140,255,0.10)", iconBg: "bg-[#5B8CFF]/10", text: "text-[#5B8CFF]" },
  responses: { color: "#06B6D4", bg: "rgba(6,182,214,0.10)", iconBg: "bg-cyan-500/10", text: "text-cyan-400" },
  interviews: { color: "#F59E0B", bg: "rgba(245,158,11,0.10)", iconBg: "bg-amber-500/10", text: "text-amber-400" },
  offers: { color: "#22C55E", bg: "rgba(34,197,94,0.10)", iconBg: "bg-emerald-500/10", text: "text-emerald-400" },
}

function buildWeeklyTrend(analytics?: Analytics | null) {
  if (!analytics) return []
  const applications = Number(analytics.applications_submitted ?? analytics.total_jobs ?? 0)
  const responses = analytics.responses != null ? Number(analytics.responses) : 0
  if (applications <= 0 && responses <= 0) return []
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
  const appsPerDay = applications > 0 ? Math.max(1, Math.round(applications / 4)) : 0
  const responsePerDay = responses > 0 ? Math.max(1, Math.round(responses / 4)) : 0
  return days.map((day, index) => ({
    day,
    applications: applications > 0 ? Math.max(0, Math.min(applications, appsPerDay + (index % 4))) : 0,
    responses: responses > 0 ? Math.max(0, Math.min(responses, responsePerDay + (index % 4))) : 0,
  }))
}

function isNoData(value: any): boolean {
  return value == null || value === undefined
}

function KpiCard({ label, value, sub, icon: Icon, semantic, emptyText }: { label: string; value: string | number; sub: string; icon: any; semantic: keyof typeof SEMANTIC; emptyText: string }) {
  const s = SEMANTIC[semantic]
  const isEmpty = isNoData(value) || value === "—" || value === ""
  return (
    <div className="rounded-xl border border-border bg-surface p-5 hover:border-border-hover transition-colors">
      <div className="flex items-center gap-3">
        <div className={`grid h-9 w-9 place-items-center rounded-lg ${s.iconBg} border border-white/[0.04]`}>
          <Icon className={`h-4 w-4 ${s.text}`} />
        </div>
        <span className="text-[11px] font-medium uppercase tracking-wider text-text-faint">{label}</span>
      </div>
      <div className={`mt-4 text-[28px] font-bold leading-none tracking-tight ${isEmpty ? "text-text-faint" : "text-text-primary"}`}>
        {isEmpty ? "—" : value}
      </div>
      <div className="mt-1 text-[11px] text-text-faint">{isEmpty ? emptyText : sub}</div>
    </div>
  )
}

export default function AnalyticsPage() {
  const { data: analytics } = useAnalytics()
  const hasAnalytics = !!analytics

  const sourceData = analytics?.applications_by_source
    ? Object.entries(analytics.applications_by_source).map(([name, value]) => ({ name, value: value as number }))
    : []
  const totalSource = sourceData.reduce((a, b) => a + b.value, 0)
  const showSourceChart = totalSource >= 3 && sourceData.length >= 2

  // Funnel with semantic distinction — responses must never fallback to emails_sent
  const applications = analytics?.applications_submitted ?? analytics?.total_jobs ?? 0
  const responsesVal = analytics?.responses
  const interviewsVal = analytics?.interviews ?? analytics?.interviews_scheduled
  const offersVal = analytics?.offers ?? analytics?.offers_received

  const hasResponses = !isNoData(responsesVal)
  const hasInterviews = !isNoData(interviewsVal)
  const hasOffers = !isNoData(offersVal)

  const funnel = [
    { name: "Applications", value: applications, hasData: true, color: SEMANTIC.applications.color },
    { name: "Responses", value: hasResponses ? (responsesVal as number) : 0, hasData: hasResponses, color: SEMANTIC.responses.color },
    { name: "Interviews", value: hasInterviews ? (interviewsVal as number) : 0, hasData: hasInterviews, color: SEMANTIC.interviews.color },
    { name: "Offers", value: hasOffers ? (offersVal as number) : 0, hasData: hasOffers, color: SEMANTIC.offers.color },
  ]
  const maxFunnel = Math.max(1, applications || 1)

  const weeklyTrend = buildWeeklyTrend(analytics)

  const chartTooltipStyle = {
    background: "#0F1217",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 10,
    fontSize: 11,
    color: "#EDEEF0",
  }

  return (
    <>
      <Topbar title="Analytics" icon={<BarChart3 className="h-4 w-4" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          {/* Header with time range and confidence legend */}
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-[18px] font-semibold tracking-tight">Insights</h2>
              <p className="text-[12px] text-text-muted">Track your job search progress — All time</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-border bg-surface px-3 py-1 text-[11px] font-medium text-text-muted">All time</span>
              <Badge variant="outline" className="text-[10px]">Measured</Badge>
            </div>
          </div>
          <div className="mb-6 flex flex-wrap gap-2 text-[10px] text-text-faint">
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#5B8CFF]" /> Measured</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-white/10 border border-border" /> No data</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-500/30" /> Insufficient data</span>
            <span className="inline-flex items-center gap-1.5"><Info className="h-3 w-3" /> Derived</span>
          </div>

          {/* KPI Row — semantic, colorful */}
          <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard label="Applications" value={applications || "—"} sub="Submitted" icon={Briefcase} semantic="applications" emptyText="No applications yet" />
            <KpiCard label="Responses" value={hasResponses ? (responsesVal as number) : "—"} sub={hasResponses ? "Replies" : "No response data yet"} icon={MessageSquare} semantic="responses" emptyText="No response data yet" />
            <KpiCard label="Interviews" value={hasInterviews ? (interviewsVal as number) : "—"} sub={hasInterviews ? "Scheduled" : "No interviews yet"} icon={Send} semantic="interviews" emptyText="No interviews yet" />
            <KpiCard label="Offers" value={hasOffers ? (offersVal as number) : "—"} sub={hasOffers ? "Received" : "No offers yet"} icon={Trophy} semantic="offers" emptyText="No offers yet" />
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {/* Application Funnel — most important */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-text-faint">
                <Filter className="h-3.5 w-3.5" /> Application Funnel
              </div>
              <div className="space-y-3">
                {funnel.map((stage, i) => {
                  const pct = stage.hasData ? Math.round((stage.value / maxFunnel) * 100) : 0
                  const prevVal = i > 0 ? (funnel[i-1].hasData ? funnel[i-1].value : 0) : stage.value
                  const conv = stage.hasData && i>0 && funnel[i-1].hasData && prevVal>0 ? Math.round((stage.value/prevVal)*100) : null
                  return (
                    <div key={stage.name}>
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-[12px] font-medium text-text-secondary flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{background: stage.color, opacity: stage.hasData ? 1 : 0.3}} />
                          {stage.name}
                        </span>
                        <span className="font-mono text-[11px]">
                          {stage.hasData ? <span className="font-semibold text-text-primary">{stage.value}</span> : <span className="text-text-faint">—</span>}
                          {conv!=null && <span className="ml-2 text-[10px] text-text-faint">{conv}%</span>}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/[0.04]">
                        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${stage.hasData ? Math.max(pct, 6) : 4}%`, background: stage.hasData ? stage.color : "rgba(255,255,255,0.08)" , opacity: stage.hasData ? 0.9 : 0.4 }} />
                      </div>
                      {i < funnel.length-1 && <div className="flex justify-center py-1"><span className="text-[10px] text-text-faint">↓</span></div>}
                    </div>
                  )
                })}
              </div>
              {!hasAnalytics && <p className="mt-3 text-center text-[11px] text-text-faint">No funnel data yet</p>}
            </div>

            {/* Opportunities by Source — adaptive */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-text-faint">Opportunities by Source</div>
              {sourceData.length === 0 ? (
                <div className="py-10 text-center">
                  <p className="text-[12px] font-medium text-text-primary">No source distribution yet</p>
                  <p className="mx-auto mt-1 max-w-[28ch] text-[11px] text-text-faint">Discover and save more jobs to see where your opportunities are coming from.</p>
                </div>
              ) : !showSourceChart ? (
                <div className="space-y-2">
                  {sourceData.map((s, i) => (
                    <div key={s.name} className="flex items-center justify-between rounded-lg border border-border/50 bg-white/[0.01] px-3 py-2.5">
                      <span className="flex items-center gap-2 text-[12px] text-text-secondary">
                        <span className="h-2 w-2 rounded-full" style={{background: ["#5B8CFF","#06B6D4","#F59E0B","#22C55E","#8B5CF6"][i%5]}} />
                        {s.name}
                      </span>
                      <span className="font-mono text-[12px] font-semibold text-text-primary">{s.value}</span>
                    </div>
                  ))}
                  <p className="pt-2 text-[10px] text-text-faint">Showing {sourceData.length} source{sourceData.length===1?"":"s"} · chart appears with more data</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={sourceData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#5C6370" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#5C6370" }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: "#EDEEF0" }} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {sourceData.map((_e, i) => (
                        <Cell key={i} fill={["#5B8CFF","#06B6D4","#F59E0B","#22C55E","#8B5CF6"][i%5]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Conversion — fix 0% trust */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-text-faint">Conversion</div>
              <div className="space-y-4">
                {[
                  { label: "Company Response", hasData: hasResponses && applications>0, value: hasResponses && applications>0 ? Math.round(((responsesVal as number)/applications)*100) : null, denom: hasResponses ? `${responsesVal} / ${applications} applications` : "No response data yet", color: SEMANTIC.responses.color },
                  { label: "Interview Conversion", hasData: hasInterviews && hasResponses && (responsesVal as number)>0, value: hasInterviews && hasResponses && (responsesVal as number)>0 ? Math.round(((interviewsVal as number)/(responsesVal as number))*100) : null, denom: hasInterviews && hasResponses ? `${interviewsVal} / ${responsesVal} responses` : "No interview data yet", color: SEMANTIC.interviews.color },
                  { label: "Referral Success", hasData: !isNoData(analytics?.referral_success_rate), value: !isNoData(analytics?.referral_success_rate) ? Math.round(analytics!.referral_success_rate) : null, denom: !isNoData(analytics?.referral_success_rate) ? "Measured" : "No referral outcomes yet", color: SEMANTIC.offers.color },
                ].map((r) => (
                  <div key={r.label}>
                    <div className="mb-1.5 flex items-center justify-between">
                      <span className="text-[12px] text-text-secondary">{r.label}</span>
                      {r.hasData && r.value!=null ? (
                        <span className="font-mono text-[12px] font-semibold text-text-primary">{r.value}%</span>
                      ) : (
                        <span className="font-mono text-[12px] text-text-faint">—</span>
                      )}
                    </div>
                    <div className="h-[3px] overflow-hidden rounded-full bg-white/[0.04]">
                      <div className="h-full rounded-full" style={{ width: r.hasData && r.value!=null ? `${Math.min(r.value,100)}%` : "0%", background: r.hasData ? r.color : "transparent" }} />
                    </div>
                    <div className="mt-1 text-[10px] text-text-faint">{r.denom}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Activity — meaningful */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-text-faint">
                <Users className="h-3.5 w-3.5" /> Activity
              </div>
              <div className="space-y-3">
                {[
                  { label: "Strong Matches", value: analytics?.strong_matches, iconColor: "text-violet-400", bg: "bg-violet-500/10", empty: "No strong matches yet" },
                  { label: "Emails Drafted", value: analytics?.emails_drafted, iconColor: "text-cyan-400", bg: "bg-cyan-500/10", empty: "No drafts yet" },
                  { label: "Emails Sent", value: analytics?.emails_sent, iconColor: "text-blue-400", bg: "bg-blue-500/10", empty: "No sends yet" },
                  { label: "Follow-ups Due", value: analytics?.followups_due, iconColor: "text-amber-400", bg: "bg-amber-500/10", empty: "No follow-ups" },
                ].map((item) => {
                  const hasVal = !isNoData(item.value)
                  return (
                    <div key={item.label} className="flex items-center justify-between rounded-lg border border-border/50 bg-white/[0.01] px-3 py-2.5">
                      <span className="flex items-center gap-2 text-[12px] text-text-secondary">
                        <span className={`grid h-7 w-7 place-items-center rounded-lg ${item.bg} border border-white/[0.04]`}>
                          <span className={`h-2 w-2 rounded-full ${item.iconColor.replace("text-","bg-")}`} />
                        </span>
                        {item.label}
                      </span>
                      {hasVal ? (
                        <span className="font-mono text-[13px] font-semibold text-text-primary">{item.value}</span>
                      ) : (
                        <span className="text-[11px] text-text-faint">—</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Weekly Trend — derived label kept */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-faint">
                  <TrendingUp className="h-3.5 w-3.5" /> Weekly Activity
                </div>
                <Badge variant="accent" status="dot">Live</Badge>
              </div>
              <p className="mb-2 text-[10px] text-text-faint">Derived estimate from totals — not measured daily history</p>
              {weeklyTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={weeklyTrend} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#5C6370" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#5C6370" }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={chartTooltipStyle} labelStyle={{ color: "#EDEEF0" }} />
                    <Line type="monotone" dataKey="applications" stroke={SEMANTIC.applications.color} strokeWidth={1.5} dot={false} name="Applications" strokeOpacity={0.9} />
                    <Line type="monotone" dataKey="responses" stroke={SEMANTIC.responses.color} strokeWidth={1.5} dot={false} name="Responses" strokeOpacity={0.9} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-[12px] text-text-faint">Not enough data yet — run discovery to see your weekly trend</p>
              )}
            </div>

            {/* Outcome funnel — keep existing but with semantic colors */}
            <div className="rounded-xl border border-border bg-surface p-5">
              <div className="mb-4 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-faint">
                <Filter className="h-3 w-3" /> Conversion Funnel
              </div>
              {(() => {
                const apps = analytics?.applications_submitted ?? analytics?.total_jobs ?? 0
                const resps = hasResponses ? (responsesVal as number) : 0
                const intervs = hasInterviews ? (interviewsVal as number) : 0
                const offs = hasOffers ? (offersVal as number) : 0
                const funnel2 = [
                  { name: "Applications", value: apps, hasData: true, color: SEMANTIC.applications.color },
                  { name: "Responses", value: resps, hasData: hasResponses, color: SEMANTIC.responses.color },
                  { name: "Interviews", value: intervs, hasData: hasInterviews, color: SEMANTIC.interviews.color },
                  { name: "Offers", value: offs, hasData: hasOffers, color: SEMANTIC.offers.color },
                ].filter(s => s.hasData || s.value>0)
                const punch2 = Math.max(1, ...funnel2.map(s=>s.value))
                if (funnel2.length===0) return <p className="py-8 text-center text-[12px] text-text-faint">No funnel data yet — submit an application</p>
                return (
                  <div className="space-y-2.5">
                    {funnel2.map((stage, i) => {
                      const pct = Math.round((stage.value / punch2) * 100)
                      const conv = i===0 ? 100 : stage.hasData && funnel2[i-1].hasData && funnel2[i-1].value>0 ? Math.round((stage.value/funnel2[i-1].value)*100) : null
                      return (
                        <div key={stage.name}>
                          <div className="mb-1 flex items-center justify-between text-[11px]">
                            <span className="flex items-center gap-1.5 text-text-secondary">
                              <span className="h-2 w-2 rounded-full" style={{background: stage.color, opacity: stage.hasData?1:0.3}} />
                              {stage.name}
                            </span>
                            <span className="font-mono font-medium text-text-primary">
                              {stage.hasData ? stage.value : <span className="text-text-faint">—</span>}
                              {conv!=null && <span className="ml-2 text-[10px] text-text-faint">{conv}%</span>}
                              {!stage.hasData && <span className="ml-2 text-[10px] text-text-faint">no data</span>}
                            </span>
                          </div>
                          <div className="h-5 overflow-hidden rounded-lg bg-white/[0.03]">
                            <div className="flex h-full items-center rounded-lg px-2 transition-all duration-500" style={{ width: `${stage.hasData?Math.max(pct,8):4}%`, background: stage.hasData? `${stage.color}26` : "transparent", borderLeft: stage.hasData? `2px solid ${stage.color}` : "2px solid rgba(255,255,255,0.06)" }}>
                              <span className="truncate text-[10px] font-medium" style={{ color: stage.hasData? stage.color : "#5C6370" }}>{stage.hasData? `${pct}%` : "—"}</span>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>
          </div>

          {/* Outcome Learning */}
          <div className="mt-4 rounded-xl border border-border bg-surface p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[11px] font-medium uppercase tracking-wider text-text-faint">Outcome Analytics — Learning</span>
              <Link to="/opportunities" className="text-[11px] text-accent hover:underline">View applications →</Link>
            </div>
            <OutcomeLearningMini />
          </div>
        </motion.div>
      </div>
    </>
  )
}

function OutcomeLearningMini() {
  const overview = useOutcomeOverview()
  const insights = useOutcomeInsights()
  const funnel = overview.data?.funnel
  if (overview.isLoading) return <div className="h-16 animate-shimmer rounded-lg" />
  if (!funnel || funnel.applications_started === 0) return <p className="text-[12px] text-text-muted">Not enough data yet — complete applications to see learning</p>
  const rates = [
    { label: "Applications", val: funnel.applications_started, color: SEMANTIC.applications.color },
    { label: "Screenings", val: funnel.screening_count, color: SEMANTIC.responses.color },
    { label: "Interviews", val: funnel.interview_count, color: SEMANTIC.interviews.color },
    { label: "Offers", val: funnel.offer_count, color: SEMANTIC.offers.color },
    { label: "Accepted", val: funnel.accepted_count, color: SEMANTIC.offers.color },
  ]
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-5 gap-2">
        {rates.map(r => (
          <div key={r.label} className="rounded-lg border border-border bg-white/[0.02] p-3 text-center">
            <div className="text-[10px] text-text-faint" style={{color: r.color}}>{r.label}</div>
            <div className="font-mono text-[14px] font-semibold" style={{color: r.color}}>{r.val}</div>
          </div>
        ))}
      </div>
      <div className="text-[11px] text-text-faint flex items-center gap-1.5">
        <AlertCircle className="h-3 w-3" />
        {insights.data?.insights?.length ? `Top insight: ${insights.data.insights[0].segment} — ${Math.round((insights.data.insights[0].interview_rate||0)*100)}% interview rate` : "Collect more data for insights"}
      </div>
    </div>
  )
}
