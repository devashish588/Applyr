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
            "h-9 w-full rounded-md border border-border bg-bg-tertiary px-3 text-[13px] text-text-primary outline-none transition placeholder:text-text-muted focus:border-accent focus:ring-2 focus:ring-accent/20",
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