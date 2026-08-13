import { Outlet } from "react-router-dom"
import { AppSidebar } from "./app-sidebar"
import { StatusBar } from "./status-bar"
import { CommandPalette } from "./command-palette"
import { useLayoutStore } from "@/store/layout-store"
import { cn } from "@/lib/utils"

export function AppLayout() {
  const collapsed = useLayoutStore((s) => s.collapsed)

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg">
      <AppSidebar />
      <main
        className={cn(
          "flex min-w-0 flex-1 flex-col overflow-hidden transition-[margin] duration-200",
          collapsed ? "ml-[56px]" : "ml-[220px]"
        )}
      >
        <div className="flex min-h-0 flex-1 flex-col">
          <Outlet />
        </div>
        <StatusBar />
      </main>
      <CommandPalette />
    </div>
  )
}