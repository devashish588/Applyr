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
        "rounded-xl border border-border bg-surface p-4 transition-colors hover:border-border-hover",
        className
      )}
    >
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium text-text-muted">
        {Icon && <Icon className="h-3.5 w-3.5 opacity-50" />}
        {label}
      </div>
      <div className="text-[24px] font-semibold leading-tight tracking-tight text-text-primary">
        {value}
      </div>
      {sub && <div className="mt-1 text-[11px] text-text-faint">{sub}</div>}
    </div>
  )
}
