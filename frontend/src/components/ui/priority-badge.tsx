import { cn } from "@/lib/utils"

type PriorityTier = "HOT" | "WARM" | "REVIEW" | "COLD" | string

interface PriorityBadgeProps {
  tier: PriorityTier
  className?: string
  size?: "sm" | "md"
}

const tierStyles: Record<string, { bg: string; text: string; dot: string }> = {
  HOT:    { bg: "bg-red/10 border-red/20",     text: "text-red",     dot: "bg-red"     },
  WARM:   { bg: "bg-amber/10 border-amber/20", text: "text-amber",   dot: "bg-amber"   },
  REVIEW: { bg: "bg-blue/10 border-blue/20",   text: "text-blue",    dot: "bg-blue"    },
  COLD:   { bg: "bg-text-muted/10 border-border", text: "text-text-muted", dot: "bg-text-muted" },
}

export function PriorityBadge({ tier, className, size = "sm" }: PriorityBadgeProps) {
  const label = tier?.toUpperCase() || "UNKNOWN"
  const style = tierStyles[label] || tierStyles.COLD

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border font-semibold uppercase tracking-wider",
        style.bg,
        style.text,
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]",
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", style.dot)} />
      {label}
    </span>
  )
}
