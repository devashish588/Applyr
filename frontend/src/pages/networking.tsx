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
      <Topbar title="Networking" icon={<Users className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-semibold">Network</h2>
              <p className="text-[12px] text-text-muted">Recruiters & contacts discovered</p>
            </div>
            <span className="text-[11px] text-text-muted">{recruiters.length} contacts</span>
          </div>

          {isLoading ? (
            <div className="space-y-3">{[1, 2, 3].map((i) => <div key={i} className="h-20 animate-shimmer rounded-lg" />)}</div>
          ) : recruiters.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border bg-surface py-16">
              <Users className="h-8 w-8 text-text-muted opacity-20" />
              <p className="text-[13px] text-text-muted">No contacts yet</p>
              <p className="text-[11px] text-text-muted">Run a discovery to find recruiters</p>
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-surface">
              {/* Table header */}
              <div className="grid grid-cols-[2fr_1.5fr_2fr_1fr_1fr] gap-2 border-b border-border px-4 py-2.5">
                {["Name", "Company", "Email", "Source", "Score"].map((h) => (
                  <span key={h} className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">{h}</span>
                ))}
              </div>
              {/* Rows */}
              {recruiters.map((r, i) => (
                <motion.div
                  key={r.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className={cn("grid grid-cols-[2fr_1.5fr_2fr_1fr_1fr] gap-2 px-4 py-3 transition hover:bg-surface-hover", i < recruiters.length - 1 && "border-b border-border")}
                >
                  <div className="min-w-0">
                    <div className="truncate text-[13px] font-medium text-text-primary">{r.name || "Unknown"}</div>
                    <div className="truncate text-[11px] text-text-muted">{r.role || r.department || ""}</div>
                  </div>
                  <div className="flex items-center gap-1.5 truncate text-[12px] text-text-secondary">
                    <Building className="h-3 w-3 shrink-0 text-text-muted" />
                    {sanitizeCompany(r.company)}
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    {r.email ? (
                      <a href={`mailto:${r.email}`} className="flex items-center gap-1 truncate text-[12px] text-accent-sub hover:underline">
                        <MailIcon className="h-3 w-3 shrink-0" />{r.email}
                      </a>
                    ) : r.linkedin ? (
                      <a href={r.linkedin} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 truncate text-[12px] text-blue hover:underline">
                        <ExternalLink className="h-3 w-3 shrink-0" />LinkedIn
                      </a>
                    ) : (
                      <span className="text-[12px] text-text-muted">—</span>
                    )}
                  </div>
                  <span className="text-[11px] text-text-muted">{r.source || "—"}</span>
                  <div className="flex items-center gap-1">
                    <Award className="h-3 w-3 text-text-muted" />
                    <span className={cn("text-[11px] font-semibold", r.confidence >= 70 ? "text-green" : r.confidence >= 40 ? "text-amber" : "text-text-muted")}>
                      {r.confidence || 0}%
                    </span>
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
