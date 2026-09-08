import { cva, type VariantProps } from "class-variance-authority"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-[10px] font-medium",
  {
    variants: {
      variant: {
        accent: "bg-accent/[0.08] text-accent-sub",
        green: "bg-green/[0.08] text-green",
        amber: "bg-amber/[0.06] text-amber",
        red: "bg-red/[0.06] text-red",
        blue: "bg-blue/[0.06] text-blue",
        neutral: "bg-white/[0.04] text-text-muted",
        outline: "border border-border bg-transparent text-text-secondary",
      },
      status: {
        none: "",
        dot: "before:mr-0.5 before:inline-block before:h-1.5 before:w-1.5 before:rounded-full before:bg-current before:opacity-60",
        pulse: "before:mr-0.5 before:inline-block before:h-1.5 before:w-1.5 before:animate-blink before:rounded-full before:bg-current before:opacity-60",
      },
    },
    defaultVariants: { variant: "neutral", status: "none" },
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