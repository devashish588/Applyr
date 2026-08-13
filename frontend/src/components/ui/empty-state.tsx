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
        compact ? "py-8" : "rounded-lg border border-dashed border-border py-14",
        className
      )}
    >
      {Icon && <Icon className={cn("text-text-muted opacity-30", compact ? "h-6 w-6" : "h-9 w-9")} />}
      <p className="text-[13px] font-medium text-text-secondary">{title}</p>
      {description && <p className="max-w-[300px] text-[12px] text-text-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}