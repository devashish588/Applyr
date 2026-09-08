import { forwardRef, type ButtonHTMLAttributes } from "react"
import { Loader2 } from "lucide-react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg text-[13px] font-medium transition-all duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-35",
  {
    variants: {
      variant: {
        primary:
          "bg-accent/90 text-white shadow-sm shadow-accent/10 hover:bg-accent hover:shadow-md hover:shadow-accent/15 active:scale-[0.98]",
        secondary: "border border-border bg-white/[0.02] text-text-primary hover:bg-white/[0.04] hover:border-border-hover",
        subtle: "bg-transparent text-text-secondary hover:bg-white/[0.03] hover:text-text-primary",
        ghost: "bg-transparent text-text-muted hover:bg-white/[0.03] hover:text-text-secondary",
        danger: "bg-red/90 text-white hover:bg-red shadow-sm",
        outline: "border border-border bg-transparent text-text-primary hover:bg-white/[0.03]",
      },
      size: {
        xs: "h-7 px-2.5 text-[11px]",
        sm: "h-8 px-3 text-[12px]",
        md: "h-9 px-4 text-[13px]",
        lg: "h-10 px-5 text-[14px]",
        icon: "h-8 w-8 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
)

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  )
)
Button.displayName = "Button"

// eslint-disable-next-line react/only-export-components
export { buttonVariants }