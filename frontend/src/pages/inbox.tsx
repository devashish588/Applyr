import { useState } from "react"
import { Mail, Send, Check, X, Edit3, ChevronDown, ChevronUp } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
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
      next.has(id) ? next.delete(id) : next.add(id)
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
      <Topbar title="Inbox" icon={<Mail className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-semibold">Inbox</h2>
              <p className="text-[12px] text-text-muted">Email configuration & drafts</p>
            </div>
            <button
              onClick={() => testMutation.mutate(undefined)}
              className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3.5 py-1.5 text-[12px] font-semibold text-text-primary transition hover:bg-surface-hover"
            >
              <Send className="h-3.5 w-3.5" /> Test Email
            </button>
          </div>

          {/* Status cards */}
          <div className="mb-4 grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-[11px] font-medium text-text-muted">Provider</div>
              <div className="mt-1 text-[13px] font-medium text-text-primary">{emailStatus?.provider || "—"}</div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-[11px] font-medium text-text-muted">Account</div>
              <div className="mt-1 truncate text-[13px] font-medium text-text-primary">{emailStatus?.from_email || "—"}</div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-[11px] font-medium text-text-muted">Status</div>
              <div className={cn("mt-1 text-[13px] font-medium", emailStatus?.configured ? "text-green" : "text-amber")}>
                {emailStatus?.configured ? "Connected" : "Not configured"}
              </div>
            </div>
          </div>

          {/* Drafts */}
          <div className="rounded-lg border border-border bg-surface p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Review & Send Drafts</span>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-text-muted">{approved.size} approved</span>
                <button
                  onClick={sendApproved}
                  disabled={approved.size === 0 || sendMutation.isPending}
                  className="flex items-center gap-1.5 rounded-md bg-gradient-to-br from-accent to-teal-600 px-3.5 py-1.5 text-[12px] font-semibold text-white shadow-[0_3px_12px] shadow-accent-glow transition disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Send className="h-3.5 w-3.5" /> Send Approved
                </button>
              </div>
            </div>

            {isLoading ? (
              <div className="space-y-2">{[1, 2, 3].map((i) => <div key={i} className="h-16 animate-shimmer rounded-lg" />)}</div>
            ) : !drafts || drafts.length === 0 ? (
              <div className="py-8 text-center text-[13px] text-text-muted">No email drafts yet</div>
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

          {/* Test email section */}
          <div className="mt-4 rounded-lg border border-border bg-surface p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Send Test Email</div>
            <div className="mt-3 flex gap-2">
              <input
                type="email"
                value={testTo}
                onChange={(e) => setTestTo(e.target.value)}
                placeholder="test@email.com"
                className="flex-1 rounded-md border border-border bg-bg-tertiary px-3 py-2 text-[12px] text-text-primary outline-none transition focus:border-accent"
              />
              <button
                onClick={() => testMutation.mutate(testTo || undefined)}
                disabled={testMutation.isPending}
                className="flex items-center gap-1.5 rounded-md bg-gradient-to-br from-accent to-teal-600 px-4 py-2 text-[12px] font-semibold text-white"
              >
                Send Test
              </button>
            </div>
            {testMutation.isSuccess && <p className="mt-2 text-[11px] text-green">✓ Test email sent!</p>}
            {testMutation.isError && <p className="mt-2 text-[11px] text-red">✗ Failed to send test email</p>}
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
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={cn(
        "rounded-lg border p-3.5 transition",
        isApproved ? "border-accent/30 bg-accent/[0.03]" : "border-border"
      )}
    >
      <div className="flex items-center gap-3">
        {/* Approval checkbox */}
        <button
          onClick={onToggleApproval}
          className={cn(
            "grid h-5 w-5 shrink-0 place-items-center rounded border transition",
            isApproved ? "border-accent bg-accent text-white" : "border-border bg-bg-tertiary"
          )}
        >
          {isApproved && <Check className="h-3 w-3" />}
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium text-text-primary">{sanitizeCompany(draft.company)}</span>
            <span className="text-[11px] text-text-muted">— {draft.title || "Role"}</span>
          </div>
          <div className="text-[12px] text-text-secondary">{draft.email_subject || "No subject"}</div>
        </div>

        {draft.fit_score != null && (
          <span className={cn("font-mono text-[11px] font-bold", scoreColor(draft.fit_score))}>{draft.fit_score}%</span>
        )}

        <button onClick={onToggleExpand} className="rounded p-1 text-text-muted transition hover:bg-surface-hover">
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
            <div className="mt-3 rounded-md border border-border bg-bg-tertiary p-3">
              <div className="mb-1 text-[10px] font-semibold uppercase text-text-muted">To: {draft.hr_email || "—"}</div>
              <div className="mb-2 text-[11px] font-semibold text-text-primary">Subject: {draft.email_subject}</div>
              <div className="whitespace-pre-wrap text-[12px] leading-relaxed text-text-secondary">{draft.email_body || "No body"}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
