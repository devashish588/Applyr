import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon?: LucideIcon
  className?: string
}

export function StatCard({ label, value, sub, icon: Icon, className }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface p-4 transition hover:border-border-hover",
        className
      )}
    >
      <div className="mb-0.5 flex items-center gap-1 text-[11px] font-medium text-text-muted">
        {Icon && <Icon className="h-3.5 w-3.5" />}
        {label}
      </div>
      <div className="text-[28px] font-bold leading-tight tracking-tight text-text-primary">
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[11px] text-text-muted">{sub}</div>}
    </div>
  )
}
