import { Settings as SettingsIcon, Check, X, ExternalLink, Send, RefreshCw } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
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
  const { data: gmail } = useGmailStatus()
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
      <Topbar title="Settings" icon={<SettingsIcon className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="mb-4">
            <h2 className="text-[15px] font-semibold">Settings</h2>
            <p className="text-[12px] text-text-muted">Configure your workspace</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Configuration */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Configuration</div>
              {config ? (
                <div className="space-y-2.5">
                  {[
                    { label: "Dry Run", value: config.dry_run ? "On" : "Off", ok: !config.dry_run },
                    { label: "Auto Apply", value: config.auto_apply ? "On" : "Off", ok: config.auto_apply },
                    { label: "Min Fit Score", value: `${config.min_fit_score}%` },
                    { label: "Max Emails/Run", value: String(config.max_emails_per_run) },
                    { label: "Max Emails/Day", value: String(config.max_per_day) },
                    { label: "Scheduler", value: config.scheduler_enabled ? config.scheduler_cron : "Disabled" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between">
                      <span className="text-[12px] text-text-secondary">{item.label}</span>
                      <span className={cn("text-[12px] font-medium", item.ok === false ? "text-amber" : item.ok ? "text-green" : "text-text-primary")}>
                        {item.value}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">Loading…</p>
              )}
            </div>

            {/* API Keys */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">API Keys</div>
              {status?.env_keys ? (
                <div className="space-y-2">
                  {Object.entries(status.env_keys).map(([key, configured]) => (
                    <div key={key} className="flex items-center gap-2">
                      <div className={cn("grid h-4 w-4 place-items-center rounded-full", configured ? "bg-green-bg text-green" : "bg-red-bg text-red")}>
                        {configured ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
                      </div>
                      <span className="font-mono text-[11px] text-text-secondary">{key}</span>
                      <span className={cn("ml-auto text-[10px]", configured ? "text-green" : "text-red")}>
                        {configured ? "Set" : "Missing"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">Loading…</p>
              )}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            {/* Email */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Email</div>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-text-secondary">Provider</span>
                  <span className="text-[12px] font-medium text-text-primary">{email?.provider || "—"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-text-secondary">Account</span>
                  <span className="truncate text-[12px] font-medium text-text-primary">{email?.from_email || "—"}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-text-secondary">Status</span>
                  <span className={cn("text-[12px] font-medium", email?.configured ? "text-green" : "text-amber")}>
                    {email?.configured ? "Connected" : "Not configured"}
                  </span>
                </div>
                {email?.gmail && (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] text-text-secondary">Gmail</span>
                      <span className={cn("text-[12px] font-medium", email.gmail.configured ? "text-green" : "text-text-muted")}>
                        {email.gmail.configured ? email.gmail.account || "Connected" : "Not connected"}
                      </span>
                    </div>
                    {!email.gmail.configured && (
                      <button
                        onClick={handleGmailConnect}
                        className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-md bg-gradient-to-br from-accent to-teal-600 px-4 py-2 text-[12px] font-semibold text-white shadow-[0_3px_12px] shadow-accent-glow"
                      >
                        <ExternalLink className="h-3.5 w-3.5" /> Connect Gmail
                      </button>
                    )}
                  </>
                )}
              </div>

              {/* Test email */}
              <div className="mt-4 border-t border-border pt-4">
                <div className="flex gap-2">
                  <input
                    type="email"
                    value={testTo}
                    onChange={(e) => setTestTo(e.target.value)}
                    placeholder="test@email.com"
                    className="flex-1 rounded-md border border-border bg-bg-tertiary px-3 py-2 text-[12px] text-text-primary outline-none focus:border-accent"
                  />
                  <button
                    onClick={() => testMutation.mutate(testTo || undefined)}
                    disabled={testMutation.isPending}
                    className="flex items-center gap-1.5 rounded-md bg-gradient-to-br from-accent to-teal-600 px-3 py-2 text-[12px] font-semibold text-white"
                  >
                    <Send className="h-3.5 w-3.5" /> Send Test
                  </button>
                </div>
                {testMutation.isSuccess && <p className="mt-2 text-[11px] text-green">✓ Test email sent!</p>}
                {testMutation.isError && <p className="mt-2 text-[11px] text-red">✗ Failed</p>}
              </div>
            </div>

            {/* Setup Status */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Setup Status</span>
                {setup && (
                  <span className="font-mono text-[11px] text-text-muted">{setup.completed}/{setup.total}</span>
                )}
              </div>
              {setup?.steps ? (
                <div className="space-y-2">
                  {setup.steps.map((step) => (
                    <div key={step.id} className="flex items-center gap-2.5">
                      <div className={cn("grid h-5 w-5 place-items-center rounded-full text-[9px]", step.ok ? "bg-green-bg text-green" : "bg-red-bg text-red")}>
                        {step.ok ? "✓" : "✗"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[12px] text-text-secondary">{step.label}</div>
                        <div className="text-[10px] text-text-muted">{step.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">Loading…</p>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </>
  )
}
