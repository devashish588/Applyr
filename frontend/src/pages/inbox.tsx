import { useState } from "react"
import { Mail, Send, Check, ChevronDown, ChevronUp, CheckCircle2, Inbox } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { useEmailDrafts, useSendEmails, useSendTestEmail } from "@/hooks/use-emails"
import { useEmailStatus } from "@/hooks/use-dashboard"
import { cn, sanitizeCompany, scoreColor } from "@/lib/utils"
import type { EmailDraft } from "@/types/api"

export default function InboxPage() {
  const { data: drafts, isLoading } = useEmailDrafts()
  const { data: emailStatus } = useEmailStatus()
  const sendMutation = useSendEmails()
  const testMutation = useSendTestEmail()
  const [approved, setApproved] = useState<Set<number>>(new Set())
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [testTo, setTestTo] = useState("")

  const toggleApproval = (id: number) => {
    setApproved((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const sendApproved = () => {
    const items = Array.from(approved).map((id) => ({ id }))
    if (items.length === 0) return
    sendMutation.mutate(items, {
      onSuccess: () => setApproved(new Set()),
    })
  }

  return (
    <>
      <Topbar title="Outreach Inbox & Drafts" icon={<Mail className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>

          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-text-primary tracking-tight">Outreach Inbox & Draft Review</h2>
              <p className="text-xs text-text-muted">Review, approve, and dispatch personalized recruiter messages</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => testMutation.mutate(undefined)}
              disabled={testMutation.isPending}
              className="h-8 text-xs gap-1.5"
            >
              <Send className="h-3.5 w-3.5" /> Test Dispatch
            </Button>
          </div>

          {/* Status Cards */}
          <div className="mb-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-border bg-bg-secondary p-4">
              <div className="text-[11px] font-medium text-text-muted">Active Email Provider</div>
              <div className="mt-1 text-xs font-semibold text-text-primary">{emailStatus?.provider || "—"}</div>
            </div>
            <div className="rounded-xl border border-border bg-bg-secondary p-4">
              <div className="text-[11px] font-medium text-text-muted">Sender Address</div>
              <div className="mt-1 truncate text-xs font-semibold text-text-primary">{emailStatus?.from_email || "—"}</div>
            </div>
            <div className="rounded-xl border border-border bg-bg-secondary p-4">
              <div className="text-[11px] font-medium text-text-muted">Connection Status</div>
              <div className={cn("mt-1 text-xs font-semibold", emailStatus?.configured ? "text-emerald-400" : "text-amber")}>
                {emailStatus?.configured ? "Connected & Ready" : "Not configured"}
              </div>
            </div>
          </div>

          {/* Drafts Section */}
          <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Inbox className="h-3.5 w-3.5 text-accent" /> Review & Send Drafts ({drafts?.length || 0})
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-muted">{approved.size} selected</span>
                <Button
                  onClick={sendApproved}
                  disabled={approved.size === 0 || sendMutation.isPending}
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                >
                  <Send className="h-3.5 w-3.5" /> Send Approved ({approved.size})
                </Button>
              </div>
            </div>

            {isLoading ? (
              <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-16 animate-pulse rounded-lg bg-white/[0.02]" />)}</div>
            ) : !drafts || drafts.length === 0 ? (
              <div className="py-12 text-center text-xs text-text-faint border border-dashed border-border/60 rounded-lg">
                No email drafts queued for review. Run the pipeline to discover roles with HR contacts.
              </div>
            ) : (
              <div className="space-y-2">
                <AnimatePresence>
                  {drafts.map((draft, i) => (
                    <DraftCard
                      key={draft.id}
                      draft={draft}
                      index={i}
                      isApproved={approved.has(draft.id)}
                      isExpanded={expandedId === draft.id}
                      onToggleApproval={() => toggleApproval(draft.id)}
                      onToggleExpand={() => setExpandedId(expandedId === draft.id ? null : draft.id)}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </div>

          {/* Test Email Section */}
          <div className="mt-6 rounded-xl border border-border bg-bg-secondary p-5 space-y-3">
            <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Send Manual Test Email</div>
            <div className="flex gap-2">
              <input
                type="email"
                value={testTo}
                onChange={(e) => setTestTo(e.target.value)}
                placeholder="recipient@example.com"
                className="h-9 flex-1 rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none transition focus:border-accent/60 placeholder:text-text-faint"
              />
              <Button
                onClick={() => testMutation.mutate(testTo || undefined)}
                disabled={testMutation.isPending}
                size="sm"
                className="h-9 text-xs gap-1.5"
              >
                Send Test
              </Button>
            </div>
            {testMutation.isSuccess && <p className="text-[11px] text-emerald-400 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Test email sent!</p>}
            {testMutation.isError && <p className="text-[11px] text-coral">Failed to send test email</p>}
          </div>

        </motion.div>
      </div>
    </>
  )
}

function DraftCard({ draft, index, isApproved, isExpanded, onToggleApproval, onToggleExpand }: {
  draft: EmailDraft; index: number; isApproved: boolean; isExpanded: boolean
  onToggleApproval: () => void; onToggleExpand: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.02 }}
      className={cn(
        "rounded-lg border p-3.5 transition text-xs",
        isApproved ? "border-accent/50 bg-accent/[0.03]" : "border-border/60 bg-white/[0.01] hover:bg-white/[0.02]"
      )}
    >
      <div className="flex items-center gap-3">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isApproved}
          onChange={onToggleApproval}
          className="rounded border-border bg-bg-secondary text-accent focus:ring-accent/20 h-4 w-4 shrink-0 cursor-pointer"
        />

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-text-primary">{sanitizeCompany(draft.company)}</span>
            <span className="text-text-muted">— {draft.title || "Role"}</span>
          </div>
          <div className="text-text-secondary truncate mt-0.5">{draft.email_subject || "No subject"}</div>
        </div>

        {draft.fit_score != null && (
          <span className={cn("font-mono text-[11px] font-semibold shrink-0", scoreColor(draft.fit_score))}>{draft.fit_score}%</span>
        )}

        <button onClick={onToggleExpand} className="rounded p-1 text-text-muted hover:text-text-primary transition">
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 rounded-lg border border-border/80 bg-black/30 p-3.5 space-y-2 text-xs">
              <div className="text-[11px] font-medium text-text-muted">Recipient: <span className="text-text-primary font-mono">{draft.hr_email || "—"}</span></div>
              <div className="text-[11px] font-medium text-text-muted">Subject: <span className="text-text-primary">{draft.email_subject}</span></div>
              <div className="whitespace-pre-wrap text-text-secondary text-[11px] leading-relaxed pt-2 border-t border-border/40">
                {draft.email_body || "No body text available."}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
