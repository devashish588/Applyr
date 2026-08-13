import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface CardProps {
  children: ReactNode
  className?: string
  interactive?: boolean
  onClick?: () => void
}

export function Card({ children, className, interactive, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-lg border border-border bg-surface",
        interactive && "cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:shadow-lg hover:shadow-black/15",
        className
      )}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  title: string
  subtitle?: string
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

export function CardHeader({ title, subtitle, action, icon, className }: CardHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between border-b border-border px-4 py-3", className)}>
      <div className="flex min-w-0 items-center gap-2">
        {icon}
        <div className="min-w-0">
          <h3 className="truncate text-[13px] font-semibold text-text-primary">{title}</h3>
          {subtitle && <p className="truncate text-[11px] text-text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}

interface CardBodyProps {
  children: ReactNode
  className?: string
  padded?: boolean
}

export function CardBody({ children, className, padded = true }: CardBodyProps) {
  return <div className={cn(padded ? "p-4" : "", className)}>{children}</div>
}