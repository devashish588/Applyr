import { useNavigate } from "react-router-dom"
import { Loader2, CheckCircle2, XCircle, Activity, ChevronRight, MousePointerClick } from "lucide-react"
import { usePipelineStore } from "@/store/pipeline-store"
import { cn } from "@/lib/utils"

export function StatusBar() {
  const navigate = useNavigate()
  const { isRunning, currentPct, currentMsg, events, error } = usePipelineStore()

  const status = error ? { icon: XCircle, color: "text-red/80", label: "Error" }
    : isRunning ? { icon: Loader2, color: "text-accent-sub", label: "Running" }
    : currentPct >= 100 || events.some((e) => e.step === "done") ? { icon: CheckCircle2, color: "text-green/80", label: "Done" }
    : { icon: Activity, color: "text-text-faint", label: "Idle" }

  const StatusIcon = status.icon

  return (
    <div className="flex h-[28px] shrink-0 items-center gap-3 border-t border-border bg-bg-secondary/60 px-4 text-[10px] text-text-faint backdrop-blur">
      {/* Left: pipeline status */}
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <StatusIcon className={cn("h-3 w-3 shrink-0", status.color, isRunning && "animate-spin")} />
        <span className={cn("shrink-0 font-medium", status.color)}>{status.label}</span>
        {isRunning && (
          <>
            <span className="h-[3px] w-24 shrink-0 overflow-hidden rounded-full bg-white/[0.04]">
              <span
                className="block h-full rounded-full bg-accent/60 transition-[width] duration-300"
                style={{ width: `${currentPct}%` }}
              />
            </span>
            <span className="shrink-0 font-mono text-[9px] text-text-faint">{Math.round(currentPct)}%</span>
            <span className="min-w-0 truncate text-text-muted">{currentMsg}</span>
          </>
        )}
      </div>

      {/* Right: quick actions */}
      <div className="flex shrink-0 items-center gap-1">
        <button
          onClick={() => navigate("/pipeline")}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-text-faint transition-colors hover:bg-white/[0.03] hover:text-text-muted"
        >
          <MousePointerClick className="h-2.5 w-2.5" />
          Pipeline
          <ChevronRight className="h-2.5 w-2.5" />
        </button>
        <button
          onClick={() => navigate("/opportunities")}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-text-faint transition-colors hover:bg-white/[0.03] hover:text-text-muted"
        >
          Apps
          <ChevronRight className="h-2.5 w-2.5" />
        </button>
      </div>
    </div>
  )
}