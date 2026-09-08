import { Settings as SettingsIcon, Check, X, ExternalLink, Send, ShieldCheck, Mail, Sliders, CheckCircle2 } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { useConfig, useSetupStatus, useGmailStatus } from "@/hooks/use-settings"
import { useEmailStatus, useSystemStatus } from "@/hooks/use-dashboard"
import { useSendTestEmail } from "@/hooks/use-emails"
import { fetchGmailAuthUrl } from "@/api/settings"
import { cn } from "@/lib/utils"
import { useState } from "react"

export default function SettingsPage() {
  const { data: config } = useConfig()
  const { data: setup } = useSetupStatus()
  const { data: email } = useEmailStatus()
  const { data: status } = useSystemStatus()
  useGmailStatus()
  const testMutation = useSendTestEmail()
  const [testTo, setTestTo] = useState("")

  const handleGmailConnect = async () => {
    try {
      const url = await fetchGmailAuthUrl()
      window.open(url, "_blank")
    } catch {
      // handle error
    }
  }

  return (
    <>
      <Topbar title="Settings & Integration" icon={<SettingsIcon className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>

          <div className="mb-6">
            <h2 className="text-base font-semibold text-text-primary tracking-tight">System Settings & Integrations</h2>
            <p className="text-xs text-text-muted">Manage API credentials, email delivery providers, and application automation parameters</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Configuration */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Sliders className="h-3.5 w-3.5 text-accent" /> Engine Configuration
                </span>
              </div>
              {config ? (
                <div className="space-y-3 pt-1 text-xs">
                  {[
                    { label: "Dry Run Mode", value: config.dry_run ? "Active (Simulation)" : "Disabled (Live)", ok: !config.dry_run },
                    { label: "Auto Apply Workflow", value: config.auto_apply ? "Enabled" : "Disabled", ok: config.auto_apply },
                    { label: "Min Match Score Threshold", value: `${config.min_fit_score}%` },
                    { label: "Max Emails per Run", value: String(config.max_emails_per_run) },
                    { label: "Max Emails per Day", value: String(config.max_per_day) },
                    { label: "Autonomous Scheduler", value: config.scheduler_enabled ? config.scheduler_cron : "Disabled" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between py-1 border-b border-border/40 last:border-0">
                      <span className="text-text-muted">{item.label}</span>
                      <span className={cn("font-medium", item.ok === false ? "text-amber" : item.ok ? "text-emerald-400" : "text-text-primary")}>
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-faint">Loading configuration parameters…</p>
              )}
            </div>

            {/* API Keys */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                <ShieldCheck className="h-3.5 w-3.5 text-accent" /> Service API Keys & Secrets
              </div>
              {status?.env_keys ? (
                <div className="space-y-2.5 pt-1">
                  {Object.entries(status.env_keys).map(([key, configured]) => (
                    <div key={key} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.01] border border-border/40">
                      <div className="flex items-center gap-2.5">
                        <div className={cn("grid h-4 w-4 place-items-center rounded-full text-[9px]", configured ? "bg-emerald-500/10 text-emerald-400" : "bg-coral/10 text-coral")}>
                          {configured ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
                        </div>
                        <span className="font-mono text-xs text-text-primary">{key}</span>
                      </div>
                      <span className={cn("text-[11px] font-medium", configured ? "text-emerald-400" : "text-coral")}>
                        {configured ? "Configured" : "Missing"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-faint">Loading environment status…</p>
              )}
            </div>

          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Email Integration */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-accent" /> Email Dispatcher Provider
              </div>
              <div className="space-y-3 pt-1 text-xs">
                <div className="flex items-center justify-between py-1 border-b border-border/40">
                  <span className="text-text-muted">Active Provider</span>
                  <span className="font-medium text-text-primary">{email?.provider || "—"}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-border/40">
                  <span className="text-text-muted">Dispatch Address</span>
                  <span className="truncate font-medium text-text-primary">{email?.from_email || "—"}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-border/40">
                  <span className="text-text-muted">Connection Status</span>
                  <span className={cn("font-medium", email?.configured ? "text-emerald-400" : "text-amber")}>
                    {email?.configured ? "Connected" : "Not configured"}
                  </span>
                </div>
                {email?.gmail && (
                  <>
                    <div className="flex items-center justify-between py-1 border-b border-border/40">
                      <span className="text-text-muted">Gmail OAuth</span>
                      <span className={cn("font-medium", email.gmail.configured ? "text-emerald-400" : "text-text-muted")}>
                        {email.gmail.configured ? email.gmail.account || "Connected" : "Not connected"}
                      </span>
                    </div>
                    {!email.gmail.configured && (
                      <Button
                        onClick={handleGmailConnect}
                        size="sm"
                        className="mt-2 w-full text-xs gap-1.5"
                      >
                        <ExternalLink className="h-3.5 w-3.5" /> Connect Gmail Account
                      </Button>
                    )}
                  </>
                )}
              </div>

              {/* Test Email */}
              <div className="mt-4 border-t border-border/60 pt-4 space-y-2">
                <label className="text-[11px] font-medium text-text-muted block">Send Test Dispatch</label>
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={testTo}
                    onChange={(e) => setTestTo(e.target.value)}
                    placeholder="test@example.com"
                    className="h-8 flex-1 rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none focus:border-accent/60 placeholder:text-text-faint"
                  />
                  <Button
                    onClick={() => testMutation.mutate(testTo || undefined)}
                    disabled={testMutation.isPending}
                    size="sm"
                    className="h-8 text-xs gap-1.5"
                  >
                    <Send className="h-3.5 w-3.5" /> Test
                  </Button>
                </div>
                {testMutation.isSuccess && <p className="text-[11px] text-emerald-400 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Test email sent successfully!</p>}
                {testMutation.isError && <p className="text-[11px] text-coral">Failed to send test email.</p>}
              </div>
            </div>

            {/* System Setup Status */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center justify-between">
                <span>System Onboarding Checklist</span>
                {setup && (
                  <span className="font-mono text-xs font-semibold text-text-primary">{setup.completed}/{setup.total} Complete</span>
                )}
              </div>
              {setup?.steps ? (
                <div className="space-y-2.5 pt-1">
                  {setup.steps.map((step) => (
                    <div key={step.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-white/[0.01] border border-border/40">
                      <div className={cn("grid h-5 w-5 place-items-center rounded-full text-[10px] shrink-0 font-bold", step.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-coral/10 text-coral")}>
                        {step.ok ? "✓" : "!"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-medium text-text-primary">{step.label}</div>
                        <div className="text-[11px] text-text-muted leading-tight">{step.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-faint">Loading setup status…</p>
              )}
            </div>

          </div>
        </motion.div>
      </div>
    </>
  )
}
