import { UserPlus, MailPlus, Search, Loader2, FileText, Command } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { usePipeline } from "@/hooks/use-pipeline"
import { useLayoutStore } from "@/store/layout-store"

interface TopbarProps {
  title: string
  icon: React.ReactNode
}

export function Topbar({ title, icon }: TopbarProps) {
  const navigate = useNavigate()
  const { isRunning, start } = usePipeline()
  const setCommandOpen = useLayoutStore((s) => s.setCommandOpen)

  return (
    <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-bg/80 px-6 py-2.5 backdrop-blur-xl">
      <div className="flex items-center gap-2.5">
        <span className="text-text-muted">{icon}</span>
        <span className="text-[14px] font-medium tracking-tight text-text-primary">{title}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => setCommandOpen(true)}
          className="flex items-center gap-2 rounded-lg border border-border bg-white/[0.02] px-3 py-1.5 text-[11px] text-text-muted transition-colors hover:border-border-hover hover:text-text-secondary"
        >
          <Search className="h-3 w-3" />
          <span>Search</span>
          <kbd className="ml-1 rounded bg-white/[0.04] px-1 py-0.5 font-mono text-[9px] text-text-faint">⌘K</kbd>
        </button>
        <button
          onClick={() => navigate("/pipeline")}
          className="rounded-lg p-2 text-text-muted transition-colors hover:bg-white/[0.03] hover:text-text-secondary"
          title="Pipeline"
        >
          <FileText className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => navigate("/network")}
          className="rounded-lg p-2 text-text-muted transition-colors hover:bg-white/[0.03] hover:text-text-secondary"
          title="Find Recruiters"
        >
          <UserPlus className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => navigate("/settings")}
          className="rounded-lg p-2 text-text-muted transition-colors hover:bg-white/[0.03] hover:text-text-secondary"
          title="Connect Gmail"
        >
          <MailPlus className="h-3.5 w-3.5" />
        </button>
        <div className="mx-1 h-4 w-px bg-border" />
        <button
          onClick={start}
          disabled={isRunning}
          className="flex items-center gap-1.5 rounded-lg bg-accent/90 px-3.5 py-1.5 text-[12px] font-medium text-white shadow-sm shadow-accent/10 transition-all hover:bg-accent hover:shadow-md hover:shadow-accent/15 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isRunning ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Searching…
            </>
          ) : (
            <>
              <Search className="h-3.5 w-3.5" />
              Run Discovery
            </>
          )}
        </button>
      </div>
    </div>
  )
}
