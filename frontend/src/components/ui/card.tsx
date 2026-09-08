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
        "rounded-xl border border-border bg-surface",
        interactive && "cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:shadow-lg hover:shadow-black/20",
        className
      )}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps {
  title?: string
  subtitle?: string
  action?: ReactNode
  icon?: ReactNode
  children?: ReactNode
  className?: string
}

export function CardHeader({ title, subtitle, action, icon, children, className }: CardHeaderProps) {
  if (children) {
    return <div className={cn("flex items-center justify-between border-b border-border px-5 py-3", className)}>{children}</div>
  }

  return (
    <div className={cn("flex items-center justify-between border-b border-border px-5 py-3", className)}>
      <div className="flex min-w-0 items-center gap-2">
        {icon && <span className="text-text-muted">{icon}</span>}
        <div className="min-w-0">
          {title && <h3 className="truncate text-[13px] font-medium text-text-primary">{title}</h3>}
          {subtitle && <p className="truncate text-[11px] text-text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  )
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h3 className={cn("text-[13px] font-medium text-text-primary", className)}>{children}</h3>
}

interface CardBodyProps {
  children: ReactNode
  className?: string
  padded?: boolean
}

export function CardBody({ children, className, padded = true }: CardBodyProps) {
  return <div className={cn(padded ? "p-5" : "", className)}>{children}</div>
}

export function CardContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("p-5", className)}>{children}</div>
}