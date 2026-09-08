import { Users, Mail as MailIcon, ExternalLink, Building, Award } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { useRecruiters } from "@/hooks/use-recruiters"
import { cn, sanitizeCompany } from "@/lib/utils"

export default function NetworkingPage() {
  const { data, isLoading } = useRecruiters()
  const recruiters = data?.recruiters || []

  return (
    <>
      <Topbar title="Network & Recruiter Intelligence" icon={<Users className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>

          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-text-primary tracking-tight">Recruiter & Contact Directory</h2>
              <p className="text-xs text-text-muted">Targeted talent acquisition contacts discovered via research agents</p>
            </div>
            <span className="text-xs font-mono font-medium text-text-muted">{recruiters.length} Contacts Discovered</span>
          </div>

          {isLoading ? (
            <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-14 animate-pulse rounded-xl bg-white/[0.02]" />)}</div>
          ) : recruiters.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/60 bg-bg-secondary py-16 text-center">
              <Users className="h-8 w-8 text-text-faint" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-text-primary">No Contacts Discovered Yet</p>
                <p className="text-xs text-text-muted max-w-xs mx-auto">Run the discovery pipeline to automatically find recruiter emails and hiring manager profiles.</p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-bg-secondary overflow-hidden shadow-sm">
              {/* Table header */}
              <div className="grid grid-cols-[2fr_1.5fr_2fr_1fr_1fr] gap-3 border-b border-border/80 bg-white/[0.02] px-5 py-3 text-[11px] font-medium uppercase tracking-wider text-text-muted">
                {["Contact Name", "Company", "Contact Info", "Source", "Confidence"].map((h) => (
                  <span key={h}>{h}</span>
                ))}
              </div>

              {/* Rows */}
              {recruiters.map((r, i) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className={cn(
                    "grid grid-cols-[2fr_1.5fr_2fr_1fr_1fr] gap-3 px-5 py-3.5 items-center text-xs transition hover:bg-white/[0.02]",
                    i < recruiters.length - 1 && "border-b border-border/40"
                  )}
                >
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-text-primary">{r.name || "Unknown Contact"}</div>
                    <div className="truncate text-[11px] text-text-muted">{r.role || r.department || "Talent Acquisition"}</div>
                  </div>
                  <div className="flex items-center gap-1.5 truncate text-text-secondary">
                    <Building className="h-3.5 w-3.5 shrink-0 text-text-faint" />
                    <span className="truncate">{sanitizeCompany(r.company)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    {r.email ? (
                      <a href={`mailto:${r.email}`} className="flex items-center gap-1.5 truncate text-accent hover:underline font-mono text-[11px]">
                        <MailIcon className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate">{r.email}</span>
                      </a>
                    ) : r.linkedin ? (
                      <a href={r.linkedin} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 truncate text-blue-400 hover:underline">
                        <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                        <span>LinkedIn Profile</span>
                      </a>
                    ) : (
                      <span className="text-text-faint">—</span>
                    )}
                  </div>
                  <span className="text-text-muted font-mono text-[11px] flex items-center gap-1">
                    {(r as any).source ? <span className="text-text-muted">{(r as any).source}</span> : <span className="text-amber flex items-center gap-1">⚠ Unverified</span>}
                    {(r as any).source_url && <a href={(r as any).source_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline text-[10px]">Source</a>}
                  </span>
                  <div className="flex flex-col items-end gap-0.5 font-mono text-[11px]">
                    <span className={cn("font-semibold", r.confidence >= 70 ? "text-emerald-400" : r.confidence >= 40 ? "text-amber" : "text-text-muted")}>
                      {r.confidence || 0}%
                    </span>
                    <span className="text-[9px] text-text-faint">{(r as any).verified_at ? `Verified ${new Date((r as any).verified_at).toLocaleDateString()}` : r.discovered_at ? `Seen ${new Date(r.discovered_at).toLocaleDateString()}` : "Source unavailable"}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </>
  )
}
