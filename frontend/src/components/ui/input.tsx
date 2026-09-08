import { forwardRef, type InputHTMLAttributes } from "react"
import { cn } from "@/lib/utils"

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const autoId = id || `input-${label?.replace(/\s+/g, "-").toLowerCase()}`
    return (
      <label className={cn("block", className)}>
        {label && (
          <span className="mb-1.5 block text-[11px] font-medium text-text-secondary">{label}</span>
        )}
        <input
          ref={ref}
          id={autoId}
          className={cn(
            "h-9 w-full rounded-lg border border-border bg-white/[0.02] px-3 text-[13px] text-text-primary outline-none transition placeholder:text-text-faint focus:border-accent/60 focus:ring-1 focus:ring-accent/15",
            error && "border-red focus:border-red focus:ring-red/20"
          )}
          {...props}
        />
        {error && <span className="mt-1 block text-[11px] text-red">{error}</span>}
      </label>
    )
  }
)
Input.displayName = "Input"