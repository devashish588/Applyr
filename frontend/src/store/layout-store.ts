import { create } from "zustand"

interface LayoutState {
  collapsed: boolean
  toggleSidebar: () => void
  setSidebar: (collapsed: boolean) => void
  commandOpen: boolean
  setCommandOpen: (open: boolean) => void
}

export const useLayoutStore = create<LayoutState>((set) => ({
  collapsed: false,
  toggleSidebar: () => set((s) => ({ collapsed: !s.collapsed })),
  setSidebar: (collapsed) => set({ collapsed }),
  commandOpen: false,
  setCommandOpen: (commandOpen) => set({ commandOpen }),
}))