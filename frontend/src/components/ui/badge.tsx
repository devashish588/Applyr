import { cva, type VariantProps } from "class-variance-authority"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-[11px] font-medium",
  {
    variants: {
      variant: {
        accent: "bg-accent-bg text-accent-sub",
        green: "bg-green-bg text-green",
        amber: "bg-amber-bg text-amber",
        red: "bg-red-bg text-red",
        blue: "bg-blue-bg text-blue",
        neutral: "bg-bg-tertiary text-text-muted",
        outline: "border border-border bg-transparent text-text-secondary",
      },
      status: {
        none: "",
        dot: "before:mr-1 before:inline-block before:h-1.5 before:w-1.5 before:rounded-full before:bg-current",
        pulse: "before:mr-1 before:inline-block before:h-1.5 before:w-1.5 before:animate-blink before:rounded-full before:bg-current",
      },
    },
    defaultVariants: { variant: "neutral", status: "default" },
  }
)

interface BadgeProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, "color">, VariantProps<typeof badgeVariants> {
  children: ReactNode
}

export function Badge({ className, variant, status, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, status }), className)} {...props}>
      {children}
    </span>
  )
}