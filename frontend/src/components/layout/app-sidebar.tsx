import { NavLink, useNavigate } from "react-router-dom"
import {
  Home, Compass, Briefcase, Wand2, Users, Mail, BarChart3, Settings,
  Zap, Search, Rocket, PanelLeftClose, PanelLeft, ChevronRight, Bot, GraduationCap,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useSystemStatus } from "@/hooks/use-dashboard"
import { useJobs } from "@/hooks/use-jobs"
import { useLayoutStore } from "@/store/layout-store"
import { Tooltip } from "@/components/ui/tooltip"

const navSections = [
  {
    label: "Hunt",
    items: [
      { path: "/discover", icon: Compass, label: "Discover Jobs" },
      { path: "/opportunities", icon: Briefcase, label: "Applications", badge: true },
      { path: "/resume", icon: Wand2, label: "Resume Studio" },
      { path: "/pipeline", icon: Rocket, label: "Pipeline" },
    ],
  },
  {
    label: "AI Assist",
    items: [
      { path: "/copilot", icon: Bot, label: "Career Copilot" },
      { path: "/interview", icon: GraduationCap, label: "Interview Prep" },
    ],
  },
  {
    label: "Network",
    items: [
      { path: "/network", icon: Users, label: "Networking" },
      { path: "/inbox", icon: Mail, label: "Inbox" },
    ],
  },
  {
    label: "Insights",
    items: [{ path: "/analytics", icon: BarChart3, label: "Analytics" }],
  },
  {
    label: "System",
    items: [{ path: "/settings", icon: Settings, label: "Settings" }],
  },
]


export function AppSidebar() {
  const navigate = useNavigate()
  const { collapsed, toggleSidebar } = useLayoutStore()
  const { data: status } = useSystemStatus()
  const { data: jobs } = useJobs()
  const isOnline = status?.status === "online"
  const jobCount = jobs?.length || 0

  const goHome = () => navigate("/")

  const renderLink = (item: { path: string; icon: React.ElementType; label: string; badge?: boolean }) => {
    const link = (
      <NavLink
        key={item.path}
        to={item.path}
        className={({ isActive }) =>
          cn(
            "group relative flex items-center rounded-md text-[13px] font-medium transition-all duration-150",
            collapsed ? "justify-center px-0 py-2" : "gap-2.5 px-3 py-2",
            isActive
              ? "bg-accent-bg text-accent-sub"
              : "text-text-secondary hover:bg-surface hover:text-text-primary"
          )
        }
      >
        {({ isActive }) => (
          <>
            {isActive && (
              <span className="absolute left-0 top-1/2 h-[18px] w-[3px] -translate-y-1/2 rounded-r-sm bg-accent" />
            )}
            <item.icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-accent" : "opacity-50")} />
            {!collapsed && (
              <>
                <span>{item.label}</span>
                {item.badge && jobCount > 0 && (
                  <span className="ml-auto rounded-full bg-accent-bg px-[7px] py-[1px] text-[10px] font-semibold text-accent-sub">
                    {jobCount}
                  </span>
                )}
              </>
            )}
          </>
        )}
      </NavLink>
    )

    if (collapsed) {
      return <Tooltip key={item.path} content={item.label} side="right">{link}</Tooltip>
    }
    return link
  }

  return (
    <aside
      className={cn(
        "fixed top-0 left-0 z-40 flex h-screen flex-col border-r border-border bg-bg-secondary transition-[width] duration-200",
        collapsed ? "w-[56px]" : "w-[220px]"
      )}
    >
      {/* Logo */}
      <div className={cn("flex items-center border-b border-border", collapsed ? "justify-center px-0 py-4" : "gap-2.5 px-[18px] py-4")}>
        <button onClick={goHome} className="grid h-[30px] w-[30px] shrink-0 place-items-center rounded-lg bg-gradient-to-br from-accent to-teal-600 text-sm font-extrabold text-white">
          <Zap className="h-4 w-4" />
        </button>
        {!collapsed && (
          <span className="truncate bg-gradient-to-r from-accent-sub to-teal-400 bg-clip-text text-base font-bold text-transparent">
            Applyr
          </span>
        )}
      </div>

      {/* Global search */}
      <div className={cn("border-b border-border py-2", collapsed ? "flex justify-center" : "px-2")}>
        <button
          onClick={() => useLayoutStore.getState().setCommandOpen(true)}
          title="Search (Ctrl K)"
          className={cn(
            "flex items-center rounded-md text-[12px] text-text-muted transition hover:bg-surface hover:text-text-primary",
            collapsed ? "justify-center py-2" : "w-full gap-2 px-2.5 py-1.5"
          )}
        >
          <Search className="h-4 w-4 shrink-0" />
          {!collapsed && (
            <>
              <span className="flex-1 text-left">Search…</span>
              <kbd className="rounded bg-bg-tertiary px-1 font-mono text-[10px] text-text-faint">⌘K</kbd>
            </>
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className={cn("flex flex-1 flex-col gap-0.5 overflow-y-auto py-2", collapsed ? "px-1.5" : "px-2")}>
        <div className="space-y-0.5">
          <NavLink
            to="/"
            className={({ isActive }) =>
              cn(
                "group relative flex items-center rounded-md text-[13px] font-medium transition-all duration-150",
                collapsed ? "justify-center px-0 py-2" : "gap-2.5 px-3 py-2",
                isActive
                  ? "bg-accent-bg text-accent-sub"
                  : "text-text-secondary hover:bg-surface hover:text-text-primary"
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && <span className="absolute left-0 top-1/2 h-[18px] w-[3px] -translate-y-1/2 rounded-r-sm bg-accent" />}
                <Home className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-accent" : "opacity-50")} />
                {!collapsed && <span>Home</span>}
              </>
            )}
          </NavLink>

          {navSections.map((section) => (
            <div key={section.label} className="mt-3">
              {!collapsed && (
                <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.6px] text-text-muted">
                  {section.label}
                </div>
              )}
              <div className="space-y-0.5">
                {section.items.map((item) => renderLink(item))}
              </div>
            </div>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className={cn("border-t border-border py-3", collapsed ? "flex flex-col items-center gap-3" : "flex items-center justify-between px-3.5")}>
        <div className={cn("flex items-center gap-[7px] text-[11px] text-text-muted", collapsed && "flex-col gap-2")}>
          <div
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              isOnline ? "bg-green shadow-[0_0_8px] shadow-green animate-blink" : "bg-red shadow-[0_0_8px] shadow-red"
            )}
          />
          {!collapsed && <span>{isOnline ? "Connected" : "Offline"}</span>}
        </div>
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-text-muted transition hover:bg-surface hover:text-text-primary"
          title={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>
    </aside>
  )
}

export function ChevronItemIcon() {
  return <ChevronRight className="h-3 w-3" />
}