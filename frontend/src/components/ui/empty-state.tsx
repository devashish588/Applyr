import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: ReactNode
  className?: string
  compact?: boolean
}

export function EmptyState({ icon: Icon, title, description, action, className, compact }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 text-center",
        compact ? "py-8" : "rounded-xl border border-dashed border-border/60 py-14",
        className
      )}
    >
      {Icon && <Icon className={cn("text-text-faint opacity-40", compact ? "h-6 w-6" : "h-8 w-8")} />}
      <p className="text-xs font-medium text-text-primary">{title}</p>
      {description && <p className="max-w-[320px] text-xs text-text-muted leading-relaxed">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}