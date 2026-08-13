import { useState, type ReactNode } from "react"
import ReactDOM from "react-dom"
import { cn } from "@/lib/utils"

interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: "top" | "bottom" | "left" | "right"
  delay?: number
  className?: string
  disabled?: boolean
}

export function Tooltip({ content, children, side = "top", delay = 200, className, disabled }: TooltipProps) {
  const [open, setOpen] = useState(false)
  const [rect, setRect] = useState<DOMRect | null>(null)
  const [coords, setCoords] = useState<{ x: number; y: number } | null>(null)

  const show = (e: React.MouseEvent<HTMLElement>) => {
    if (disabled) return
    const el = e.currentTarget.getBoundingClientRect()
    setRect(el)
    setTimeout(() => setCoords({ x: el.left + el.width / 2, y: el.top }), delay)
    setTimeout(() => setOpen(true), delay)
  }
  const hide = () => {
    setOpen(false)
    setCoords(null)
  }

  const placements: Record<string, React.CSSProperties> = {
    top: { left: (rect?.left || 0) + (rect?.width || 0) / 2, top: (rect?.top || 0) - 8, transform: "translate(-50%, -100%)" },
    bottom: { left: (rect?.left || 0) + (rect?.width || 0) / 2, top: (rect?.bottom || 0) + 8, transform: "translate(-50%, 0)" },
    left: { left: (rect?.left || 0) - 8, top: (rect?.top || 0) + (rect?.height || 0) / 2, transform: "translate(-100%, -50%)" },
    right: { left: (rect?.right || 0) + 8, top: (rect?.top || 0) + (rect?.height || 0) / 2, transform: "translate(0, -50%)" },
  }

  const tooltip = open && coords ? (
    ReactDOM.createPortal(
      <div
        className={cn(
          "pointer-events-none fixed z-[70] max-w-[240px] whitespace-pre-wrap rounded-md border border-border bg-bg-tertiary px-2.5 py-1.5 text-[11px] leading-relaxed text-text-primary shadow-xl",
          className
        )}
        style={placements[side]}
        key={coords.x}
      >
        {content}
      </div>,
      document.body
    )
  ) : null

  return (
    <span className="inline-flex" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {tooltip}
    </span>
  )
}