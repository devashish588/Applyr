import { CheckCircle2, XCircle, HelpCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface EvidenceItem {
  label: string
  status: "satisfied" | "missing" | "unknown"
}

interface EvidenceListProps {
  items: EvidenceItem[]
  title?: string
  className?: string
  compact?: boolean
}

const statusConfig = {
  satisfied: { icon: CheckCircle2, color: "text-green",      label: "Matched" },
  missing:   { icon: XCircle,      color: "text-red",        label: "Gap"     },
  unknown:   { icon: HelpCircle,   color: "text-text-muted", label: "Unknown" },
}

export function EvidenceList({ items, title, className, compact = false }: EvidenceListProps) {
  if (!items || items.length === 0) return null

  const grouped = {
    satisfied: items.filter(i => i.status === "satisfied"),
    missing:   items.filter(i => i.status === "missing"),
    unknown:   items.filter(i => i.status === "unknown"),
  }

  return (
    <div className={cn("space-y-3", className)}>
      {title && <div className="section-label">{title}</div>}

      {(["satisfied", "missing", "unknown"] as const).map(status => {
        const group = grouped[status]
        if (group.length === 0) return null
        const config = statusConfig[status]
        const Icon = config.icon

        return (
          <div key={status} className="space-y-1">
            <div className={cn("flex items-center gap-1.5 text-[11px] font-medium", config.color)}>
              <Icon className="h-3 w-3" />
              <span>{config.label} ({group.length})</span>
            </div>
            <div className={cn("flex flex-wrap gap-1.5", compact ? "pl-0" : "pl-4")}>
              {group.map((item, i) => (
                <span
                  key={i}
                  className={cn(
                    "inline-block rounded-md border px-2 py-0.5 text-[11px]",
                    status === "satisfied"
                      ? "border-green/20 bg-green/5 text-green"
                      : status === "missing"
                        ? "border-red/20 bg-red/5 text-red"
                        : "border-border bg-bg-tertiary text-text-muted"
                  )}
                >
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/** Helper to convert skill_gaps array from Studio API into EvidenceItems */
export function skillGapsToEvidence(gaps: any[]): EvidenceItem[] {
  if (!gaps) return []
  return gaps.map(g => ({
    label: g.skill || g.name || "Unknown",
    status: g.status === "SATISFIED" ? "satisfied"
          : g.gap_type === "UNSUPPORTED" ? "missing"
          : "unknown"
  }))
}
