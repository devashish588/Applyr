import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom"
import { useApplication, useApplicationTimeline, useUpdateApplicationState, useApplyApplication, usePostOutcome } from "@/hooks/use-applications"
import { useInterviews, useCreateInterview, useCompleteInterview, useCancelInterview, useInterviewPrep, useFollowUps, useCreateFollowUp, useReviewFollowUp, useApproveFollowUp, useSendFollowUp } from "@/hooks/use-interviews"
import { useJobDetail } from "@/hooks/use-jobs"
import { Topbar } from "@/components/layout/topbar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { getNextActionForApplication } from "@/lib/next-action"
import { useState } from "react"
import { ArrowLeft, Briefcase, Calendar, Clock, Sparkles, Send, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

export default function ApplicationDetailPage() {
  const { appId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get("tab") || "timeline"
  const navigate = useNavigate()
  const id = appId ? parseInt(appId, 10) : null
  const { data: app, isLoading, isError } = useApplication(id)
  const { data: timeline } = useApplicationTimeline(id)
  const { data: jobData } = useJobDetail(app?.job_id || null)
  const job: any = (jobData as any)?.job || jobData
  const { data: interviews } = useInterviews(id)
  const { data: prep } = useInterviewPrep(id)
  const { data: followUps } = useFollowUps(id)
  const updateState = useUpdateApplicationState()
  const apply = useApplyApplication()
  const postOutcome = usePostOutcome()
  const createInterview = useCreateInterview()
  const completeInterview = useCompleteInterview()
  const cancelInterview = useCancelInterview()
  const createFollowUp = useCreateFollowUp()
  const reviewFU = useReviewFollowUp()
  const approveFU = useApproveFollowUp()
  const sendFU = useSendFollowUp()
  const [outcome, setOutcome] = useState("ACCEPTED")

  if (isLoading) return (
    <>
      <Topbar title="Application Detail" icon={<Briefcase className="h-4 w-4 text-text-muted" />} />
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-32 w-full rounded-xl" />
      </div>
    </>
  )

  if (isError || !app) return (
    <>
      <Topbar title="Application Detail" icon={<Briefcase className="h-4 w-4 text-text-muted" />} />
      <div className="p-12 max-w-md mx-auto text-center space-y-3">
        <p className="text-sm text-text-primary">Application record not found.</p>
        <Button size="sm" variant="outline" onClick={() => navigate(-1)}>Back to Opportunities</Button>
      </div>
    </>
  )

  const next = getNextActionForApplication(app)
  const isMutating = updateState.isPending || apply.isPending || postOutcome.isPending

  return (
    <>
      <Topbar title="Application Detail" icon={<Briefcase className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto space-y-6">

        {/* Back Navigation & Main Header Card */}
        <div className="space-y-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="text-text-muted hover:text-text-primary px-0 hover:bg-transparent -ml-1 text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1.5" /> Back to pipeline
          </Button>

          <Card className="rounded-xl border-border bg-bg-secondary p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-lg font-semibold text-text-primary tracking-tight">
                    {job?.title || app.job_title_snapshot || "Application"}
                  </h1>
                  <span className="text-text-faint">·</span>
                  <span className="text-sm font-medium text-text-secondary">
                    {job?.company || app.company_snapshot || "Company"}
                  </span>
                </div>
                <p className="text-xs text-text-muted">
                  Next Step: <span className="text-text-secondary font-medium">{next.label}</span> — {next.description}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Badge variant={app.current_state === "APPLIED" ? "accent" : app.current_state === "OFFER" ? "green" : "neutral"}>
                  {app.current_state}
                </Badge>
                {app.final_outcome && (
                  <Badge variant="outline">Outcome: {app.final_outcome}</Badge>
                )}
                <Link to={next.to}>
                  <Button size="sm" variant={next.variant === "primary" ? "primary" : "outline"} disabled={isMutating} className="h-8 text-xs">
                    {next.label}
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        </div>

        {/* Tabbed Detail Sections */}
        <Card className="rounded-xl border-border overflow-hidden">
          <div className="flex border-b border-border/80 bg-white/[0.01] px-5 pt-3 gap-6">
            {[
              { id: "timeline", label: "Timeline Events" },
              { id: "interview", label: "Interviews & Prep" },
              { id: "followups", label: "Follow-ups" },
              { id: "outcome", label: "Outcome Record" },
            ].map(t => (
              <button
                key={t.id}
                onClick={() => setSearchParams({ tab: t.id })}
                className={cn(
                  "pb-3 text-xs font-medium transition border-b-2 -mb-px",
                  tab === t.id
                    ? "border-accent text-accent"
                    : "border-transparent text-text-muted hover:text-text-primary"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          <CardContent className="p-5 text-xs">
            {tab === "timeline" && (
              <div className="space-y-4">
                {!timeline?.length ? (
                  <p className="text-text-faint py-4 text-center">No timeline events recorded yet.</p>
                ) : (
                  <div className="space-y-2">
                    {timeline.map((ev: any) => (
                      <div key={ev.id} className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-white/[0.01]">
                        <div className="flex items-center gap-3">
                          <span className="font-semibold text-text-primary font-mono text-[11px]">{ev.event_type}</span>
                          <span className="text-text-muted">{ev.payload || ""}</span>
                        </div>
                        <span className="text-[11px] text-text-faint font-mono">
                          {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="pt-4 border-t border-border/50 flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" disabled={isMutating} onClick={() => updateState.mutate({ appId: app.id, state: "SCREENING" })} className="h-8 text-xs">
                    Move to SCREENING
                  </Button>
                  <Button variant="outline" size="sm" disabled={isMutating} onClick={() => updateState.mutate({ appId: app.id, state: "INTERVIEW" })} className="h-8 text-xs">
                    Move to INTERVIEW
                  </Button>
                  <Button size="sm" disabled={isMutating} onClick={() => apply.mutate(app.id)} className="h-8 text-xs">
                    Mark as APPLIED
                  </Button>
                </div>
              </div>
            )}

            {tab === "interview" && (
              <div className="space-y-6">
                <div className="space-y-3">
                  <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Scheduled Interviews</div>
                  {!interviews?.length ? (
                    <p className="text-text-faint text-xs">No interview rounds scheduled yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {interviews.map((iv: any) => (
                        <div key={iv.id} className="p-3 rounded-lg border border-border bg-bg-secondary flex justify-between items-center">
                          <div>
                            <div className="font-semibold text-text-primary">{iv.stage} Round · <span className="text-accent">{iv.status}</span></div>
                            <div className="text-[11px] text-text-muted">{iv.scheduled_at ? new Date(iv.scheduled_at).toLocaleString() : "Date TBD"}</div>
                            {iv.notes && <div className="text-[11px] text-text-muted mt-1">{iv.notes}</div>}
                          </div>
                            <div className="flex gap-2">
                            <Button size="sm" disabled={completeInterview.isPending} onClick={() => completeInterview.mutate({ id: iv.id })} className="h-7 text-xs">
                              Complete
                            </Button>
                            <Button size="sm" variant="ghost" disabled={cancelInterview.isPending} onClick={() => cancelInterview.mutate(iv.id)} className="h-7 text-xs text-red">
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <Button size="sm" variant="outline" disabled={createInterview.isPending} onClick={() => createInterview.mutate({ appId: app.id, payload: { stage: "TECHNICAL", scheduled_at: new Date().toISOString() } })} className="h-8 text-xs">
                    Schedule Technical Round
                  </Button>
                </div>

                <div className="pt-4 border-t border-border/50 space-y-3">
                  <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center justify-between">
                    <span>Interview Preparation Kit</span>
                    <Link to={`/interview?appId=${app.id}`}>
                      <Button variant="ghost" size="sm" className="h-6 text-[11px] text-accent p-0 hover:bg-transparent">
                        Open Full Interactive Prep →
                      </Button>
                    </Link>
                  </div>
                  {!prep ? (
                    <p className="text-text-faint text-xs">No prep kit loaded yet.</p>
                  ) : (
                    <div className="p-3 rounded-lg border border-border/60 bg-white/[0.01] space-y-2 text-xs">
                      <div>Active Stage: <Badge variant="outline">{prep.stage || app.current_state}</Badge></div>
                      {prep.likely_questions?.length ? (
                        <div className="space-y-1 pt-1">
                          <span className="font-medium text-text-secondary">Sample Questions:</span>
                          <ul className="list-disc pl-4 text-text-muted space-y-0.5">
                            {prep.likely_questions.slice(0, 3).map((q: string, i: number) => <li key={i}>{q}</li>)}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>
              </div>
            )}

            {tab === "followups" && (
              <div className="space-y-4">
                <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Follow-up Communication Pipeline</div>
                {!followUps?.length ? (
                  <p className="text-text-faint text-xs">No follow-ups drafted for this application.</p>
                ) : (
                  <div className="space-y-2">
                    {followUps.map((f: any) => (
                      <div key={f.id} className="p-3 rounded-lg border border-border bg-bg-secondary space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="font-semibold text-text-primary">{f.follow_up_type} · {f.channel}</span>
                          <Badge variant={f.status === "APPROVED" ? "accent" : "outline"}>{f.status}</Badge>
                        </div>
                        <div className="text-[11px] text-text-muted italic">{f.message_preview?.slice(0, 150)}...</div>
                        <div className="flex gap-2 pt-1">
                          {f.status === "DRAFT" && <Button size="sm" variant="outline" disabled={reviewFU.isPending} onClick={() => reviewFU.mutate(f.id)} className="h-7 text-xs">Move to Review</Button>}
                          {f.status === "REVIEW" && <Button size="sm" disabled={approveFU.isPending} onClick={() => approveFU.mutate(f.id)} className="h-7 text-xs">Approve</Button>}
                          {f.status === "APPROVED" && <Button size="sm" disabled={sendFU.isPending} onClick={() => sendFU.mutate(f.id)} className="h-7 text-xs">Dispatch Send</Button>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <Button size="sm" variant="outline" disabled={createFollowUp.isPending} onClick={() => createFollowUp.mutate({ appId: app.id, payload: { follow_up_type: "POST_APPLICATION", channel: "EMAIL", scheduled_at: new Date().toISOString() } })} className="h-8 text-xs">
                  Draft Post-Application Follow-up
                </Button>
                <p className="text-[11px] text-text-faint">State progression: DRAFT → REVIEW → APPROVED → SENT. Manual confirmation required.</p>
              </div>
            )}

            {tab === "outcome" && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg border border-border bg-bg-secondary space-y-3">
                  <div className="text-xs font-medium text-text-primary">
                    State: <span className="font-semibold text-accent">{app.current_state}</span> {app.final_outcome ? `· Outcome: ${app.final_outcome}` : ""}
                  </div>
                  {app.current_state === "OFFER" && (
                    <div className="flex items-center gap-2">
                      <select value={outcome} onChange={e => setOutcome(e.target.value)} className="h-8 rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none">
                        <option value="ACCEPTED">ACCEPTED</option>
                        <option value="REJECTED">REJECTED</option>
                        <option value="WITHDRAWN">WITHDRAWN</option>
                        <option value="UNKNOWN">UNKNOWN</option>
                      </select>
                      <Button size="sm" disabled={postOutcome.isPending} onClick={() => postOutcome.mutate({ appId: app.id, outcome })} className="h-8 text-xs">
                        Record Outcome
                      </Button>
                    </div>
                  )}
                  {app.current_state === "CLOSED" && (
                    <div className="text-xs text-text-muted">Final Outcome Recorded: <strong className="text-text-primary">{app.final_outcome || "NONE"}</strong></div>
                  )}
                </div>
                <Link to="/analytics">
                  <Button variant="ghost" size="sm" className="text-xs text-accent px-0 hover:bg-transparent">
                    View Pipeline Outcome Analytics →
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

      </div>
    </>
  )
}
