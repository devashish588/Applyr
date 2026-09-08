import { cn } from "@/lib/utils"

interface MatchScoreProps {
  score: number | null | undefined
  label?: string
  showBar?: boolean
  size?: "sm" | "md" | "lg"
  className?: string
}

function scoreColor(score: number): string {
  if (score >= 75) return "text-green"
  if (score >= 55) return "text-amber"
  return "text-text-muted"
}

function barColor(score: number): string {
  if (score >= 75) return "bg-green"
  if (score >= 55) return "bg-amber"
  return "bg-text-muted"
}

export function MatchScore({ score, label = "Match", showBar = true, size = "md", className }: MatchScoreProps) {
  const value = score ?? 0
  const display = score != null ? `${value}` : "—"

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <div className="flex items-baseline gap-1.5">
        <span
          className={cn(
            "font-mono font-bold",
            score != null ? scoreColor(value) : "text-text-faint",
            size === "lg" ? "text-2xl" : size === "md" ? "text-lg" : "text-sm"
          )}
        >
          {display}
        </span>
        {score != null && (
          <span className="text-[11px] text-text-faint font-normal">/ 100</span>
        )}
        {label && (
          <span className="text-[11px] text-text-muted ml-1">{label}</span>
        )}
      </div>

      {showBar && score != null && (
        <div className="h-1 w-full max-w-[120px] rounded-full bg-border/60 overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-500", barColor(value))}
            style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
          />
        </div>
      )}
    </div>
  )
}
