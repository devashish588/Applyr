import { Settings as SettingsIcon, Check, X, ExternalLink, Send, ShieldCheck, Mail, Sliders, CheckCircle2, Globe, Plus, Trash2, FlaskConical, FileText, Upload, Eye } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { useConfig, useSetupStatus, useGmailStatus } from "@/hooks/use-settings"
import { useEmailStatus, useSystemStatus } from "@/hooks/use-dashboard"
import { useSendTestEmail } from "@/hooks/use-emails"
import { fetchGmailAuthUrl } from "@/api/settings"
import { cn } from "@/lib/utils"
import { useState, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchJobSources, createJobSource, updateJobSource, deleteJobSource, testJobSource, fetchJobSourcesHealth } from "@/api/job_sources"
import { fetchMasterResume, uploadMasterResume, removeMasterResume, resumeFileUrl } from "@/api/resume"

export default function SettingsPage() {
  const { data: config } = useConfig()
  const { data: setup } = useSetupStatus()
  const { data: email } = useEmailStatus()
  const { data: status } = useSystemStatus()
  useGmailStatus()
  const testMutation = useSendTestEmail()
  const [testTo, setTestTo] = useState("")
  const qc = useQueryClient()
  const { data: jobSourcesData } = useQuery({ queryKey: ["job-sources"], queryFn: fetchJobSources })
  const { data: healthData } = useQuery({ queryKey: ["job-sources-health"], queryFn: fetchJobSourcesHealth })
  const [newUrl, setNewUrl] = useState("")
  const [newName, setNewName] = useState("")
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const createMut = useMutation({ mutationFn: createJobSource, onSuccess: () => { qc.invalidateQueries({ queryKey: ["job-sources"] }); qc.invalidateQueries({ queryKey: ["job-sources-health"] }); setNewUrl(""); setNewName("") } })
  const toggleMut = useMutation({ mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateJobSource(id, { enabled }), onSuccess: () => { qc.invalidateQueries({ queryKey: ["job-sources"] }); qc.invalidateQueries({ queryKey: ["job-sources-health"] }) } })
  const deleteMut = useMutation({ mutationFn: deleteJobSource, onSuccess: () => { qc.invalidateQueries({ queryKey: ["job-sources"] }); qc.invalidateQueries({ queryKey: ["job-sources-health"] }) } })

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

          <MasterResumeCard />

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

          {/* Job Sources (Multi-Source Discovery) */}
          <div className="mt-6 rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
            <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
              <Globe className="h-3.5 w-3.5 text-accent" /> Job Sources — Independent Discovery
            </div>
            <p className="text-[11px] text-text-muted">Configured sources are executed independently per run. Each shows adapter (Search/GenericHTML/RSS/JSON/ATS) and health (SUCCESS/NO_RESULTS/TIMEOUT/HTTP_ERROR/BLOCKED/ROBOTS_DISALLOWED/...). No silent fallback — failures are visible here and on Pipeline Status.</p>
            <div className="flex gap-2">
              <input value={newUrl} onChange={(e) => setNewUrl(e.target.value)} placeholder="https://company.com/careers or https://boards.greenhouse.io/company or https://.../feed.xml" className="h-8 flex-1 rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none focus:border-accent/60 placeholder:text-text-faint" />
              <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Name (optional)" className="h-8 w-36 rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none focus:border-accent/60 placeholder:text-text-faint" />
              <Button size="sm" className="h-8 text-xs gap-1.5" disabled={!newUrl.trim() || createMut.isPending} onClick={() => createMut.mutate({ url: newUrl.trim(), name: newName.trim() || undefined })}>
                <Plus className="h-3.5 w-3.5" /> Add Source
              </Button>
            </div>
            {createMut.isError && <p className="text-[11px] text-coral">Failed to add source.</p>}
            <div className="space-y-1.5 pt-1 max-h-[420px] overflow-y-auto">
              {(healthData?.sources || jobSourcesData?.sources || []).map((s:any) => {
                const perf = s.performance || {}
                const isBuilt = s.is_builtin ?? s.id?.startsWith("builtin-")
                const role = s.source_role || "UNKNOWN"
                const primary = s.primary_mode || s.source_type?.toUpperCase() || "AUTO"
                const modeLabel = ({SEARCH:"Search discovery",HTML:"Direct source",RSS:"RSS feed",JSON:"JSON/API",ATS:"ATS/API"} as any)[primary] || primary
                const directLabel = s.direct_fetch_allowed ? "Direct: Allowed" : "Direct: Disabled"
                const searchLabel = s.search_discovery_allowed ? "Search: Allowed" : "Search: Disabled"
                return (
                <div key={s.id} className="flex items-center justify-between rounded-lg px-3 py-2 border border-border/40 bg-white/[0.01] gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium text-text-primary">{s.name} <span className="text-text-faint font-normal">• {s.host}</span> {isBuilt ? <span className="ml-1 rounded bg-accent/10 px-1 py-0.5 text-[9px] text-accent">BUILT-IN</span> : <span className="ml-1 rounded bg-white/5 px-1 py-0.5 text-[9px] text-text-faint">CUSTOM</span>} <span className="ml-1 rounded bg-white/[0.03] px-1 py-0.5 text-[9px] text-text-faint">{role}</span></div>
                    <div className="truncate text-[11px] text-text-muted font-mono">{s.url}</div>
                    <div className="text-[10px] text-text-faint">{modeLabel} • {role} • {s.enabled ? "✓ Enabled" : "disabled"} • {directLabel} • {searchLabel} {s.failure_category ? `• ${s.failure_category}` : ""} {s.last_job_count ? `• ${s.last_job_count} jobs` : ""} {s.last_error ? `• ${s.last_error.slice(0,60)}` : ""} {perf.attempts ? `• ${perf.attempts} attempts ${perf.success_rate}%` : ""} {perf.avg_duration_ms ? `• ${perf.avg_duration_ms}ms avg` : ""} {s.parser_health ? `• ⚠ ${s.parser_health}` : ""} {s.observed_mode ? `• Observed: ${s.observed_mode}` : ""}</div>
                    {testResults[s.id] && (
                      <div className={cn("mt-1 rounded px-2 py-1 text-[11px] border", testResults[s.id].status==="success" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-red/10 border-red/20 text-red")}>
                        Test: {testResults[s.id].mode || testResults[s.id].adapter} {testResults[s.id].mode_label ? `(${testResults[s.id].mode_label})` : ""} • {testResults[s.id].failure_category} • {testResults[s.id].jobs_found} jobs • {testResults[s.id].duration_ms}ms {testResults[s.id].fallback_used ? "• fallback" : ""} {testResults[s.id].error ? `• ${testResults[s.id].error.slice(0,100)}` : ""} {testResults[s.id].sample?.length ? `• sample: ${testResults[s.id].sample[0]?.title?.slice(0,40)}` : ""}
                      </div>
                    )}
                  </div>
                    <div className="flex items-center gap-1 shrink-0">
                    <Button size="sm" variant="ghost" className="h-7 text-[11px] px-2" disabled={toggleMut.isPending} onClick={() => toggleMut.mutate({ id: s.id, enabled: !s.enabled })}>
                      {s.enabled ? "Disable" : "Enable"}
                    </Button>
                    <Button size="sm" variant="ghost" className="h-7 text-[11px] px-2 gap-1" onClick={async () => {
                      try { const r = await testJobSource(s.id); setTestResults(prev => ({ ...prev, [s.id]: r })) } catch { setTestResults(prev => ({ ...prev, [s.id]: { status:"failed", failure_category:"UNKNOWN", jobs_found:0, duration_ms:0, error:"Test failed" }})) }
                    }}>
                      <FlaskConical className="h-3 w-3" /> Test
                    </Button>
                    {!s.id.startsWith("builtin-") && (
                      <Button size="sm" variant="ghost" className="h-7 text-[11px] px-2 text-coral" disabled={deleteMut.isPending} onClick={() => deleteMut.mutate(s.id)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </div>
                )
              })}
              {(!jobSourcesData?.sources || jobSourcesData.sources.length===0) && <p className="text-xs text-text-faint">No sources configured — built-ins will be seeded on first pipeline run.</p>}
            </div>
          </div>

        </motion.div>
      </div>
    </>
  )
}

function MasterResumeCard() {
  const qc = useQueryClient()
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["master-resume"], queryFn: fetchMasterResume })
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const resume = data?.resume || null
  const status = data?.status || "NONE"

  const uploadMut = useMutation({
    mutationFn: uploadMasterResume,
    onSuccess: () => {
      setUploadError(null)
      setConfirmRemove(false)
      qc.invalidateQueries({ queryKey: ["master-resume"] })
      qc.invalidateQueries({ queryKey: ["resumeHistory"] })
      qc.invalidateQueries({ queryKey: ["config"] })
    },
    onError: (e: any) => {
      setUploadError(e?.response?.data?.error || "Upload failed")
    },
  })
  const removeMut = useMutation({
    mutationFn: removeMasterResume,
    onSuccess: () => {
      setConfirmRemove(false)
      qc.invalidateQueries({ queryKey: ["master-resume"] })
      qc.invalidateQueries({ queryKey: ["resumeHistory"] })
    },
    onError: (e: any) => {
      setUploadError(e?.response?.data?.error || "Remove failed")
    },
  })

  const busy = uploadMut.isPending || removeMut.isPending
  const badge = status === "READY" ? "text-emerald-400" : status === "FAILED" ? "text-coral" : status === "PROCESSING" ? "text-amber" : "text-text-faint"

  return (
    <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
      <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
        <FileText className="h-3.5 w-3.5 text-accent" /> Master Resume
      </div>
      {isLoading ? (
        <p className="text-xs text-text-faint">Loading resume status…</p>
      ) : isError ? (
        <div className="space-y-2">
          <p className="text-xs text-coral">Could not load resume status (network error).</p>
          <Button size="sm" variant="ghost" className="h-7 text-[11px]" onClick={() => refetch()}>Retry</Button>
        </div>
      ) : !resume ? (
        <div className="space-y-3">
          <p className="text-xs font-medium text-text-primary">No active resume selected.</p>
          <p className="text-[11px] text-text-muted">Resume-based matching and Application Studio preparation may be limited until a resume is uploaded.</p>
          <div className="flex items-center gap-2">
            <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) uploadMut.mutate(f)
              e.target.value = ""
            }} />
            <Button size="sm" className="h-8 text-xs gap-1.5" disabled={busy} onClick={() => fileRef.current?.click()}>
              <Upload className="h-3.5 w-3.5" /> {busy ? "Uploading…" : "Upload Resume"}
            </Button>
          </div>
          {uploadError && <p className="text-[11px] text-coral">{uploadError}</p>}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-xs font-medium text-text-primary">{resume.filename}</div>
              <div className="text-[11px] text-text-muted">
                Uploaded: {resume.uploaded_at ? new Date(resume.uploaded_at).toLocaleString() : "—"} • Status: <span className={cn("font-medium", badge)}>{status}</span>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <a href={resumeFileUrl(resume.id)} target="_blank" rel="noopener noreferrer" className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] text-text-secondary hover:bg-white/[0.04]">
                <Eye className="h-3 w-3" /> View
              </a>
              <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt" className="hidden" onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadMut.mutate(f)
                e.target.value = ""
              }} />
              <Button size="sm" variant="ghost" className="h-7 text-[11px]" disabled={busy} onClick={() => fileRef.current?.click()}>
                {busy ? "Replacing…" : "Replace"}
              </Button>
              {!confirmRemove ? (
                <Button size="sm" variant="ghost" className="h-7 text-[11px] text-coral" disabled={busy} onClick={() => setConfirmRemove(true)}>
                  <Trash2 className="h-3 w-3" /> Remove
                </Button>
              ) : (
                <span className="flex items-center gap-1 text-[11px]">
                  <span className="text-text-muted">Remove active resume? Existing applications will remain unchanged.</span>
                  <Button size="sm" variant="ghost" className="h-7 text-[11px]" onClick={() => setConfirmRemove(false)}>Cancel</Button>
                  <Button size="sm" className="h-7 text-[11px]" disabled={busy} onClick={() => removeMut.mutate()}>Remove</Button>
                </span>
              )}
            </div>
          </div>
          {uploadError && <p className="text-[11px] text-coral">{uploadError}</p>}
          {status === "FAILED" && <p className="text-[11px] text-amber">Parsing failed. Previous active resume remains active where applicable.</p>}
        </div>
      )}
    </div>
  )
}
