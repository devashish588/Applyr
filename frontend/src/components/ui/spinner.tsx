import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface SpinnerProps {
  className?: string
  size?: number
  label?: string
}

export function Spinner({ className, size = 18, label }: SpinnerProps) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-text-muted", className)}>
      <Loader2 className="animate-spin" style={{ width: size, height: size }} />
      {label && <span className="text-[12px]">{label}</span>}
    </span>
  )
}