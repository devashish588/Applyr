import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom"
import { useApplication, useApplicationTimeline, useUpdateApplicationState, useApplyApplication, usePostOutcome } from "@/hooks/use-applications"
import { useInterviews, useCreateInterview, useCompleteInterview, useCancelInterview, useInterviewPrep, useFollowUps, useCreateFollowUp, useReviewFollowUp, useApproveFollowUp, useSendFollowUp } from "@/hooks/use-interviews"
import { useJobDetail } from "@/hooks/use-jobs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { getNextActionForApplication } from "@/lib/next-action"
import { useState } from "react"

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

  if (isLoading) return <div className="p-6"><Skeleton className="h-32 w-full" /></div>
  if (isError || !app) return <div className="p-6"><p className="text-sm">Something went wrong. Try again.</p><Button variant="ghost" onClick={() => navigate(-1)}>Back</Button></div>

  const next = getNextActionForApplication(app)
  const isMutating = updateState.isPending || apply.isPending || postOutcome.isPending

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <Button variant="ghost" onClick={() => navigate(-1)}>← Back</Button>

      <Card>
        <CardHeader>
          <CardTitle className="flex justify-between">
            <span>{job?.title || app.job_title_snapshot || "Application"} · {job?.company || app.company_snapshot}</span>
            <Badge>{app.current_state}</Badge>
          </CardTitle>
          {app.final_outcome && <div className="text-sm">Outcome: {app.final_outcome}</div>}
          <div className="text-sm text-text-muted">Next: {next.label} — {next.description}</div>
          <Link to={next.to}><Button variant={next.variant} disabled={isMutating}>{next.label}</Button></Link>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 border-b pb-2">
            {["timeline", "interview", "followups", "outcome"].map(t => (
              <button key={t} onClick={() => setSearchParams({ tab: t })} className={`px-3 py-1 text-sm ${tab===t ? "font-bold border-b-2 border-accent" : "text-text-muted"}`}>{t}</button>
            ))}
          </div>

          {tab==="timeline" && (
            <div className="mt-4 space-y-2">
              {!timeline?.length && <p className="text-sm text-text-muted">No timeline yet</p>}
              {timeline?.map((ev:any) => (
                <div key={ev.id} className="flex gap-2 text-sm border-b py-2">
                  <span className="font-medium">{ev.event_type}</span>
                  <span className="text-text-muted">{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}</span>
                  <span>{ev.payload || ""}</span>
                </div>
              ))}
              <div className="flex gap-2 mt-4">
                <Button variant="outline" disabled={isMutating} onClick={() => updateState.mutate({ appId: app.id, state: "SCREENING" })}>Move to Screening</Button>
                <Button variant="outline" disabled={isMutating} onClick={() => updateState.mutate({ appId: app.id, state: "INTERVIEW" })}>Move to Interview</Button>
                <Button variant="outline" disabled={isMutating} onClick={() => apply.mutate(app.id)}>Apply (APPLIED)</Button>
              </div>
            </div>
          )}

          {tab==="interview" && (
            <div className="mt-4 space-y-4">
              {!interviews?.length && <p className="text-sm text-text-muted">No interviews scheduled</p>}
              {interviews?.map((iv:any) => (
                <div key={iv.id} className="border p-3 rounded text-sm">
                  <div>{iv.stage} · {iv.status} {iv.scheduled_at ? new Date(iv.scheduled_at).toLocaleString() : ""}</div>
                  {iv.notes && <div className="text-xs text-text-muted">{iv.notes}</div>}
                  <div className="flex gap-2 mt-2">
                    <Button size="sm" disabled={completeInterview.isPending} onClick={() => completeInterview.mutate({ id: iv.id })}>Complete</Button>
                    <Button size="sm" variant="ghost" disabled={cancelInterview.isPending} onClick={() => cancelInterview.mutate(iv.id)}>Cancel</Button>
                  </div>
                </div>
              ))}
              <Button disabled={createInterview.isPending} onClick={() => createInterview.mutate({ appId: app.id, payload: { stage: "TECHNICAL", scheduled_at: new Date().toISOString() } })}>Schedule Interview</Button>

              <div className="border-t pt-4">
                <h4 className="font-semibold">Interview Prep</h4>
                {!prep ? <p className="text-sm text-text-muted">No prep yet. Generate via application.</p> : (
                  <div className="text-sm space-y-2">
                    <div>Stage: {prep.stage || app.current_state}</div>
                    {prep.candidate_evidence && <div>Candidate evidence: {JSON.stringify(prep.candidate_evidence).slice(0,200)}</div>}
                    {prep.likely_questions?.length ? <ul className="list-disc pl-5">{prep.likely_questions.slice(0,3).map((q:string,i:number)=><li key={i}>{q}</li>)}</ul> : <p className="text-xs">Likely questions unavailable</p>}
                    {prep.behavioral_questions && <div>Behavioral: {prep.behavioral_questions.length} questions</div>}
                    {prep.technical_questions && <div>Technical: {prep.technical_questions.length} questions</div>}
                    {prep.checklist && <div>Checklist: {prep.checklist.length} items</div>}
                    <div className="text-xs text-text-muted">Disclaimer: AI-generated prep, verify facts.</div>
                    <div className="text-xs">UNKNOWN remains UNKNOWN — not fabricated.</div>
                  </div>
                )}
                <Link to={`/interview?appId=${app.id}`}><Button variant="outline" className="mt-2">Open Full Prep</Button></Link>
              </div>
            </div>
          )}

          {tab==="followups" && (
            <div className="mt-4 space-y-4">
              {!followUps?.length && <p className="text-sm text-text-muted">No follow-up drafted</p>}
              {followUps?.map((f:any) => (
                <div key={f.id} className="border p-3 rounded text-sm">
                  <div>{f.follow_up_type} · {f.channel} · {f.status}</div>
                  <div className="text-xs">{f.message_preview?.slice(0,120)}</div>
                  <div className="flex gap-2 mt-2">
                    {f.status==="DRAFT" && <Button size="sm" disabled={reviewFU.isPending} onClick={() => reviewFU.mutate(f.id)}>Move to Review</Button>}
                    {f.status==="REVIEW" && <Button size="sm" disabled={approveFU.isPending} onClick={() => approveFU.mutate(f.id)}>Approve</Button>}
                    {f.status==="APPROVED" && <Button size="sm" disabled={sendFU.isPending} onClick={() => sendFU.mutate(f.id)}>Send</Button>}
                    <span className="text-xs text-text-muted">DRAFT→REVIEW→APPROVED→SENT (explicit)</span>
                  </div>
                </div>
              ))}
              <Button disabled={createFollowUp.isPending} onClick={() => createFollowUp.mutate({ appId: app.id, payload: { follow_up_type: "POST_APPLICATION", channel: "EMAIL", scheduled_at: new Date().toISOString() } })}>Draft Follow-up</Button>
              <p className="text-xs text-text-muted">Draft is not sent. Review and approve explicitly before send. Never auto-send.</p>
            </div>
          )}

          {tab==="outcome" && (
            <div className="mt-4 space-y-4">
              <div className="text-sm">Current: {app.current_state} {app.final_outcome ? `· ${app.final_outcome}` : ""}</div>
              {app.current_state==="OFFER" && (
                <div className="flex gap-2">
                  <select value={outcome} onChange={e=>setOutcome(e.target.value)} className="border rounded px-2 py-1 text-sm">
                    <option>ACCEPTED</option><option>REJECTED</option><option>WITHDRAWN</option><option>UNKNOWN</option>
                  </select>
                  <Button disabled={postOutcome.isPending} onClick={() => postOutcome.mutate({ appId: app.id, outcome })}>Record outcome</Button>
                </div>
              )}
              {app.current_state==="CLOSED" && <div className="text-sm">Final outcome: {app.final_outcome || "NONE"} (valid)</div>}
              <Link to="/analytics"><Button variant="ghost">View Analytics → Learning</Button></Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
