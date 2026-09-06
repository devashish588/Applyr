import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import ReactDOM from "react-dom"
import { AnimatePresence, motion } from "framer-motion"
import {
  Home, Compass, Briefcase, Wand2, Users, Mail, BarChart3, Settings,
  CornerDownLeft, Rocket, Search, ArrowRight, X, Bot, GraduationCap,
} from "lucide-react"
import { useLayoutStore } from "@/store/layout-store"
import { cn } from "@/lib/utils"

interface Command {
  label: string
  group: string
  icon: string
  hint?: string
  path?: string
  action?: () => void
}

export function CommandPalette() {
  const { commandOpen, setCommandOpen } = useLayoutStore()
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [activeIdx, setActiveIdx] = useState(0)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setCommandOpen(!commandOpen)
      }
      if (e.key === "Escape") setCommandOpen(false)
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [commandOpen, setCommandOpen])

  useEffect(() => setActiveIdx(0), [query, commandOpen])

  const commands: Command[] = useMemo(() => {
    const go = (path: string) => () => { setCommandOpen(false); navigate(path) }
    return [
      { label: "Home", group: "Navigate", icon: "home", path: "/", action: go("/") },
      { label: "Discover Jobs", group: "Navigate", icon: "compass", path: "/discover", action: go("/discover") },
      { label: "Applications", group: "Navigate", icon: "kanban", path: "/opportunities", action: go("/opportunities") },
      { label: "Pipeline", group: "Navigate", icon: "rocket", path: "/pipeline", action: go("/pipeline") },
      { label: "Resume Studio", group: "Navigate", icon: "wand", path: "/resume", action: go("/resume") },
      { label: "Career Copilot", group: "Navigate", icon: "bot", path: "/copilot", action: go("/copilot") },
      { label: "Interview Prep", group: "Navigate", icon: "graduation", path: "/interview", action: go("/interview") },
      { label: "Application Studio", group: "Navigate", icon: "wand", path: "/studio/1", action: go("/studio/1") },
      { label: "Networking", group: "Navigate", icon: "users", path: "/network", action: go("/network") },
      { label: "Inbox", group: "Navigate", icon: "mail", path: "/inbox", action: go("/inbox") },
      { label: "Analytics", group: "Navigate", icon: "analytics", path: "/analytics", action: go("/analytics") },
      { label: "Settings", group: "Navigate", icon: "settings", path: "/settings", action: go("/settings") },
    ]
  }, [navigate, setCommandOpen])

  const icons: Record<string, React.ReactNode> = {
    home: <Home className="h-4 w-4" />, compass: <Compass className="h-4 w-4" />,
    kanban: <Briefcase className="h-4 w-4" />, rocket: <Rocket className="h-4 w-4" />,
    wand: <Wand2 className="h-4 w-4" />, users: <Users className="h-4 w-4" />,
    mail: <Mail className="h-4 w-4" />, analytics: <BarChart3 className="h-4 w-4" />,
    settings: <Settings className="h-4 w-4" />, search: <Search className="h-4 w-4" />,
    bot: <Bot className="h-4 w-4" />, graduation: <GraduationCap className="h-4 w-4" />,
  }

  const filtered = query.trim()
    ? commands.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
    : commands

  const onSelect = (cmd: Command) => cmd.action?.()

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, filtered.length - 1)) }
    if (e.key === "ArrowUp") { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, 0)) }
    if (e.key === "Enter") { e.preventDefault(); if (filtered[activeIdx]) onSelect(filtered[activeIdx]) }
  }

  return ReactDOM.createPortal(
    <AnimatePresence>
      {commandOpen && (
        <div className="fixed inset-0 z-[80] flex items-start justify-center px-4 pt-[12vh]">
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setCommandOpen(false)}
            className="absolute inset-0 bg-black/50 backdrop-blur-[2px]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.98, y: -8 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
            className="relative w-full max-w-[540px] overflow-hidden rounded-xl border border-border bg-bg-secondary shadow-2xl"
          >
            {/* Search input */}
            <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
              <Search className="h-4 w-4 text-text-muted" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Search pages and actions…"
                className="flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
              />
              <button onClick={() => setCommandOpen(false)} className="text-text-muted hover:text-text-primary">
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Results */}
            <div onMouseDown={(e) => e.preventDefault()} className="max-h-[320px] overflow-y-auto p-1.5">
              {filtered.length === 0 ? (
                <div className="px-4 py-8 text-center text-[12px] text-text-muted">No results for “{query}”</div>
              ) : (
                filtered.map((cmd, i) => (
                  <button
                    key={cmd.label}
                    onClick={() => onSelect(cmd)}
                    onMouseDown={(e) => { e.preventDefault(); onSelect(cmd) }}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-[13px] transition",
                      i === activeIdx ? "bg-accent-bg text-text-primary" : "text-text-secondary"
                    )}
                  >
                    <span className={cn("shrink-0", i === activeIdx ? "text-accent-sub" : "text-text-muted")}>
                      {cmd.icon ? icons[cmd.icon] : null}
                    </span>
                    <span className="flex-1">{cmd.label}</span>
                    {i === activeIdx ? (
                      <CornerDownLeft className="h-3.5 w-3.5 opacity-60" />
                    ) : (
                      <ArrowRight className="h-3 w-3 opacity-0" />
                    )}
                  </button>
                ))
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  )
}