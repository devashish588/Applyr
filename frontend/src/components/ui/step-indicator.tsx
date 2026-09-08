import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface Step {
  label: string
  status: "complete" | "active" | "upcoming"
}

interface StepIndicatorProps {
  steps: Step[]
  className?: string
}

export function StepIndicator({ steps, className }: StepIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-0", className)}>
      {steps.map((step, i) => (
        <div key={i} className="flex items-center">
          {/* Step circle + label */}
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "grid h-6 w-6 place-items-center rounded-full text-[10px] font-bold transition shrink-0",
                step.status === "complete"
                  ? "bg-green text-white"
                  : step.status === "active"
                    ? "bg-accent text-white ring-2 ring-accent/30"
                    : "bg-bg-tertiary text-text-muted border border-border"
              )}
            >
              {step.status === "complete" ? (
                <Check className="h-3 w-3" />
              ) : (
                i + 1
              )}
            </div>
            <span
              className={cn(
                "text-[12px] font-medium whitespace-nowrap",
                step.status === "complete"
                  ? "text-green"
                  : step.status === "active"
                    ? "text-accent"
                    : "text-text-muted"
              )}
            >
              {step.label}
            </span>
          </div>

          {/* Connector line */}
          {i < steps.length - 1 && (
            <div
              className={cn(
                "mx-3 h-px w-8 flex-shrink-0",
                step.status === "complete" ? "bg-green/40" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  )
}

/** Helper to derive Studio step statuses from studio data */
export function getStudioSteps(studio: any, approvals: { resume: boolean; cover: boolean }): Step[] {
  const hasMatch = !!(studio?.match || studio?.components?.match)
  const hasTailoring = !!(studio?.tailoring_proposal?.status === "READY" || studio?.tailored_resume?.status === "READY")
  const hasReview = approvals.resume

  return [
    { label: "Match",   status: hasMatch ? "complete" : "active" },
    { label: "Tailor",  status: hasTailoring ? "complete" : hasMatch ? "active" : "upcoming" },
    { label: "Review",  status: hasReview ? "complete" : hasTailoring ? "active" : "upcoming" },
    { label: "Apply",   status: hasReview ? "active" : "upcoming" },
  ]
}
