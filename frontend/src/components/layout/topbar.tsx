import { Upload, UserPlus, MailPlus, Search, Loader2, FileText, Command } from "lucide-react"
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
    <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-bg/85 px-6 py-3 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-base font-semibold">
          <span className="opacity-60">{icon}</span>
          <span>{title}</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => setCommandOpen(true)}
          className="mr-1 flex items-center gap-2 rounded-md border border-border bg-bg-tertiary px-3 py-1.5 text-[12px] text-text-muted transition hover:border-border-hover hover:text-text-primary"
        >
          <Command className="h-3.5 w-3.5" />
          <span>Quick Search</span>
          <kbd className="ml-1 rounded bg-bg px-1 font-mono text-[9px] text-text-faint">⌘K</kbd>
        </button>
        <button
          onClick={() => navigate("/pipeline")}
          className="flex items-center gap-1.5 rounded-md bg-transparent px-2.5 py-1.5 text-[13px] text-text-secondary transition hover:bg-surface hover:text-text-primary"
          title="Pipeline"
        >
          <FileText className="h-4 w-4" />
        </button>
        <button
          onClick={() => navigate("/network")}
          className="flex items-center gap-1.5 rounded-md bg-transparent px-2.5 py-1.5 text-[13px] text-text-secondary transition hover:bg-surface hover:text-text-primary"
          title="Find Recruiters"
        >
          <UserPlus className="h-4 w-4" />
        </button>
        <button
          onClick={() => navigate("/settings")}
          className="flex items-center gap-1.5 rounded-md bg-transparent px-2.5 py-1.5 text-[13px] text-text-secondary transition hover:bg-surface hover:text-text-primary"
          title="Connect Gmail"
        >
          <MailPlus className="h-4 w-4" />
        </button>
        <div className="mx-1 h-5 w-px bg-border" />
        <button
          onClick={start}
          disabled={isRunning}
          className="flex items-center gap-1.5 rounded-md bg-gradient-to-br from-accent to-teal-600 px-4 py-2 text-[13px] font-semibold text-white shadow-[0_3px_12px] shadow-accent-glow transition hover:-translate-y-0.5 hover:shadow-[0_6px_24px] hover:shadow-accent-glow disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Searching…
            </>
          ) : (
            <>
              <Search className="h-4 w-4" />
              Run Discovery
            </>
          )}
        </button>
      </div>
    </div>
  )
}
