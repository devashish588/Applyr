import { useEffect } from "react"
import ReactDOM from "react-dom"
import { AnimatePresence, motion } from "framer-motion"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface DrawerProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  title?: string
  side?: "left" | "right" | "bottom"
  width?: number
  footer?: React.ReactNode
}

export function Drawer({ open, onClose, children, title, side = "right", width = 420, footer }: DrawerProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [open, onClose])

  const position = {
    right: { x: width },
    left: { x: -width },
    bottom: { y: 400 },
  }[side]

  return ReactDOM.createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
          />
          <motion.div
            initial={position}
            animate={{ x: 0, y: 0 }}
            exit={position}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className={cn(
              "absolute flex flex-col bg-bg-secondary shadow-2xl",
              side === "right" && "right-0 top-0 h-full border-l border-border",
              side === "left" && "left-0 top-0 h-full border-r border-border",
              side === "bottom" && "bottom-0 left-0 right-0 border-t border-border"
            )}
            style={side !== "bottom" ? { width } : undefined}
          >
            {title && (
              <div className="flex items-center justify-between border-b border-border px-5 py-4">
                <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
                <button onClick={onClose} className="rounded-md p-1 text-text-muted transition hover:bg-surface hover:text-text-primary">
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
            <div className="flex-1 overflow-y-auto p-5">{children}</div>
            {footer && <div className="border-t border-border p-4">{footer}</div>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  )
}