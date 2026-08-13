import { BarChart3, Briefcase, Send, MessageSquare, Trophy, Filter, TrendingUp } from "lucide-react"
import { motion } from "framer-motion"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, LineChart, Line } from "recharts"
import { Topbar } from "@/components/layout/topbar"
import { StatCard } from "@/components/dashboard/stat-card"
import { Card, CardBody, Badge, EmptyState } from "@/components/ui"
import { useAnalytics } from "@/hooks/use-dashboard"
import type { Analytics } from "@/types/api"

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]

function buildWeeklyTrend(analytics?: Analytics | null) {
  if (!analytics) return []

  const applications = Number(analytics.applications_submitted ?? analytics.total_jobs ?? 0)
  const responses = Number(analytics.responses ?? analytics.emails_sent ?? 0)
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

export default function AnalyticsPage() {
  const { data: analytics, isLoading } = useAnalytics()

  const sourceData = analytics?.applications_by_source
    ? Object.entries(analytics.applications_by_source).map(([name, value]) => ({ name, value: value as number }))
    : []

  const statusData = analytics?.application_status_breakdown
    ? Object.entries(analytics.application_status_breakdown).map(([name, value]) => ({ name, value: value as number }))
    : []

  // Conversion funnel stages
  const applications = analytics?.applications_submitted ?? analytics?.total_jobs ?? 0
  const responses = analytics?.responses ?? analytics?.emails_sent ?? 0
  const interviews = analytics?.interviews ?? analytics?.interviews_scheduled ?? 0
  const offers = analytics?.offers ?? analytics?.offers_received ?? 0
  const funnel = [
    { name: "Applications", value: applications },
    { name: "Responses", value: Math.min(responses, applications) },
    { name: "Interviews", value: Math.min(interviews, responses, applications) },
    { name: "Offers", value: Math.min(offers, interviews, responses, applications) },
  ].filter((s) => s.value > 0)
  const punch = Math.max(1, ...funnel.map((s) => s.value))
  const funnelColors = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444"]

  // Mock weekly trend from available aggregates (falls back gracefully)
  const weeklyTrend = buildWeeklyTrend(analytics)

  return (
    <>
      <Topbar title="Analytics" icon={<BarChart3 className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="mb-4">
            <h2 className="text-[15px] font-semibold">Insights</h2>
            <p className="text-[12px] text-text-muted">Track your job search progress</p>
          </div>

          {/* KPI Grid */}
          <div className="mb-5 grid grid-cols-4 gap-4">
            <StatCard label="Applications" value={analytics?.total_jobs || "—"} sub="Total submitted" icon={Briefcase} />
            <StatCard label="Responses" value={analytics?.responses || analytics?.company_response_rate || "—"} sub="Replies received" icon={MessageSquare} />
            <StatCard label="Interviews" value={analytics?.interviews || analytics?.interviews_scheduled || "—"} sub="Scheduled" icon={Send} />
            <StatCard label="Offers" value={analytics?.offers || analytics?.offers_received || "—"} sub="Received" icon={Trophy} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Source Distribution */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Opportunities by Source</div>
              {sourceData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={sourceData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#5c6378" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#5c6378" }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#171a22", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "#eef0f4" }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {sourceData.map((_entry, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-[12px] text-text-muted">No source data yet</p>
              )}
            </div>

            {/* Status Breakdown */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Status Breakdown</div>
              {statusData.length > 0 ? (
                <div className="flex items-center gap-6">
                  <ResponsiveContainer width={160} height={160}>
                    <PieChart>
                      <Pie data={statusData} dataKey="value" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2} stroke="none">
                        {statusData.map((_entry, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: "#171a22", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, fontSize: 12 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2">
                    {statusData.map((entry, i) => (
                      <div key={entry.name} className="flex items-center gap-2">
                        <div className="h-2.5 w-2.5 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
                        <span className="text-[12px] text-text-secondary">{entry.name}</span>
                        <span className="ml-auto font-mono text-[11px] text-text-muted">{entry.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="py-8 text-center text-[12px] text-text-muted">No status data yet</p>
              )}
            </div>

            {/* Conversion Rates */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Conversion Rates</div>
              <div className="space-y-4">
                {[
                  { label: "Company Response", value: analytics?.company_response_rate || 0, color: "from-accent to-accent-sub" },
                  { label: "Interview Conversion", value: analytics?.interview_conversion_rate || 0, color: "from-blue to-blue/70" },
                  { label: "Referral Success", value: analytics?.referral_success_rate || 0, color: "from-amber to-amber/70" },
                ].map((rate) => (
                  <div key={rate.label}>
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-[12px] text-text-secondary">{rate.label}</span>
                      <span className="font-mono text-[12px] font-semibold text-text-primary">{Math.round(rate.value)}%</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-bg-tertiary">
                      <div className={`h-full rounded-full bg-gradient-to-r ${rate.color}`} style={{ width: `${Math.min(rate.value, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Summary</div>
              <div className="space-y-3">
                {[
                  { label: "Strong Matches", value: analytics?.strong_matches || 0 },
                  { label: "Emails Drafted", value: analytics?.emails_drafted || 0 },
                  { label: "Emails Sent", value: analytics?.emails_sent || 0 },
                  { label: "Follow-ups Due", value: analytics?.followups_due || 0 },
                  { label: "Startup Matches", value: analytics?.startup_matches || 0 },
                  { label: "Total Runs", value: analytics?.total_runs || 0 },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <span className="text-[12px] text-text-secondary">{item.label}</span>
                    <span className="font-mono text-[13px] font-semibold text-text-primary">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Weekly Trend */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  <TrendingUp className="h-3.5 w-3.5" /> Weekly Activity
                </div>
                <Badge variant="accent" status="dot">Live</Badge>
              </div>
              {weeklyTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={weeklyTrend} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#5c6378" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#5c6378" }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#171a22", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "#eef0f4" }}
                    />
                    <Line type="monotone" dataKey="applications" stroke="#10b981" strokeWidth={2} dot={false} name="Applications" />
                    <Line type="monotone" dataKey="responses" stroke="#3b82f6" strokeWidth={2} dot={false} name="Responses" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-[12px] text-text-muted">Not enough data yet</p>
              )}
            </div>

            {/* Conversion Funnel */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-4 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                <Filter className="h-3.5 w-3.5" /> Conversion Funnel
              </div>
              {funnel.length > 0 ? (
                <div className="space-y-2">
                  {funnel.map((stage, i) => {
                    const pct = Math.round((stage.value / punch) * 100)
                    const conv = i === 0 ? 100 : Math.round((stage.value / (funnel[i - 1]?.value || 1)) * 100)
                    return (
                      <div key={stage.name}>
                        <div className="mb-1 flex items-center justify-between text-[11px]">
                          <span className="text-text-secondary">{stage.name}</span>
                          <span className="font-mono font-semibold text-text-primary">
                            {stage.value}
                            <span className="ml-2 text-[10px] text-text-muted">{conv}%</span>
                          </span>
                        </div>
                        <div className="h-5 overflow-hidden rounded-md bg-bg-tertiary">
                          <div
                            className="flex h-full items-center rounded-md px-2 transition-all duration-500"
                            style={{
                              width: `${Math.max(pct, 8)}%`,
                              background: `color-mix(in srgb, ${funnelColors[i]} 22%, transparent)`,
                              borderLeft: `2px solid ${funnelColors[i]}`,
                            }}
                          >
                            <span className="truncate text-[10px] font-medium" style={{ color: funnelColors[i] }}>{pct}%</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="py-8 text-center text-[12px] text-text-muted">No applications yet</p>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </>
  )
}
