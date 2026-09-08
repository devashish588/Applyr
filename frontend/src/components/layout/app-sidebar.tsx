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
import { ApplyrLogo } from "@/components/ui/logo"

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
            "group relative flex items-center rounded-lg text-[13px] font-medium transition-all duration-150",
            collapsed ? "justify-center px-0 py-2.5" : "gap-2.5 px-3 py-[7px]",
            isActive
              ? "bg-white/[0.04] text-text-primary"
              : "text-text-muted hover:bg-white/[0.03] hover:text-text-secondary"
          )
        }
      >
        {({ isActive }) => (
          <>
            {isActive && (
              <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-r bg-accent opacity-80" />
            )}
            <item.icon className={cn(
              "h-[16px] w-[16px] shrink-0 transition-colors",
              isActive ? "text-text-primary" : "text-text-muted group-hover:text-text-secondary"
            )} />
            {!collapsed && (
              <>
                <span className="truncate">{item.label}</span>
                {item.badge && jobCount > 0 && (
                  <span className="ml-auto rounded-full bg-white/[0.06] px-[6px] py-[1px] text-[10px] font-medium text-text-secondary tabular-nums">
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
        collapsed ? "w-[52px]" : "w-[220px]"
      )}
    >
      {/* Logo */}
      <div className={cn(
        "flex items-center border-b border-border",
        collapsed ? "justify-center px-0 py-3.5" : "px-4 py-3.5"
      )}>
        <button onClick={goHome} className="cursor-pointer focus:outline-none">
          <ApplyrLogo showWordmark={!collapsed} size="sm" />
        </button>
      </div>

      {/* Global search */}
      <div className={cn("border-b border-border py-2", collapsed ? "flex justify-center" : "px-2.5")}>
        <button
          onClick={() => useLayoutStore.getState().setCommandOpen(true)}
          title="Search (Ctrl K)"
          className={cn(
            "flex items-center rounded-lg text-[12px] text-text-muted transition-colors hover:bg-white/[0.03] hover:text-text-secondary",
            collapsed ? "justify-center py-2" : "w-full gap-2 px-2.5 py-[6px]"
          )}
        >
          <Search className="h-3.5 w-3.5 shrink-0" />
          {!collapsed && (
            <>
              <span className="flex-1 text-left">Search…</span>
              <kbd className="rounded bg-white/[0.04] px-1.5 py-0.5 font-mono text-[9px] text-text-faint">⌘K</kbd>
            </>
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className={cn("flex flex-1 flex-col gap-0.5 overflow-y-auto py-2.5", collapsed ? "px-1.5" : "px-2")}>
        <div className="space-y-0.5">
          <NavLink
            to="/"
            className={({ isActive }) =>
              cn(
                "group relative flex items-center rounded-lg text-[13px] font-medium transition-all duration-150",
                collapsed ? "justify-center px-0 py-2.5" : "gap-2.5 px-3 py-[7px]",
                isActive
                  ? "bg-white/[0.04] text-text-primary"
                  : "text-text-muted hover:bg-white/[0.03] hover:text-text-secondary"
              )
            }
          >
            {({ isActive }) => (
              <>
                {isActive && <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-r bg-accent opacity-80" />}
                <Home className={cn("h-[16px] w-[16px] shrink-0", isActive ? "text-text-primary" : "text-text-muted")} />
                {!collapsed && <span>Home</span>}
              </>
            )}
          </NavLink>

          {navSections.map((section) => (
            <div key={section.label} className="mt-4">
              {!collapsed && (
                <div className="px-3 pb-1.5 text-[10px] font-medium uppercase tracking-[0.06em] text-text-faint">
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
      <div className={cn(
        "border-t border-border py-3",
        collapsed ? "flex flex-col items-center gap-3" : "flex items-center justify-between px-3.5"
      )}>
        <div className={cn("flex items-center gap-2 text-[11px] text-text-muted", collapsed && "flex-col gap-2")}>
          <div
            className={cn(
              "h-[6px] w-[6px] rounded-full",
              isOnline ? "bg-green/70 shadow-[0_0_6px] shadow-green/30" : "bg-red/70 shadow-[0_0_6px] shadow-red/30"
            )}
          />
          {!collapsed && <span className="text-text-faint">{isOnline ? "Connected" : "Offline"}</span>}
        </div>
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1.5 text-text-faint transition-colors hover:bg-white/[0.03] hover:text-text-muted"
          title={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? <PanelLeft className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
        </button>
      </div>
    </aside>
  )
}

export function ChevronItemIcon() {
  return <ChevronRight className="h-3 w-3" />
}