import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "./button"

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (size: number) => void
  className?: string
}

export function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange, className }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1
  const end = Math.min(total, page * pageSize)

  const seen = new Set<number>()
  const items: number[] = []
  const add = (p: number) => { if (!seen.has(p)) { seen.add(p); items.push(p) } }
  add(1); add(pages)
  for (let p = page - 1; p <= page + 1; p++) if (p > 1 && p < pages) add(p)
  items.sort((a, b) => a - b)

  const rendered: ("ellipsis" | number)[] = []
  for (let i = 0; i < items.length; i++) {
    if (i > 0 && items[i] - items[i - 1] > 1) {
      rendered.push("ellipsis")
    }
    rendered.push(items[i])
  }

  return (
    <div className={cn("flex items-center justify-between gap-3 py-2", className)}>
      <div className="text-[11px] text-text-muted">
        {start}–{end} of {total}
      </div>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="h-7 w-7" disabled={page <= 1} onClick={() => onPageChange(1)} aria-label="First">
          <ChevronsLeft className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" disabled={page <= 1} onClick={() => onPageChange(page - 1)} aria-label="Previous">
          <ChevronLeft className="h-3.5 w-3.5" />
        </Button>
        {rendered.map((it, i) =>
          it === "ellipsis" ? (
            <span key={`e${i}`} className="px-1 text-text-muted">…</span>
          ) : (
            <button
              key={it}
              onClick={() => onPageChange(it)}
              className={cn(
                "grid h-7 w-7 place-items-center rounded-md text-[12px] font-medium transition",
                it === page ? "bg-accent-bg text-accent-sub" : "text-text-secondary hover:bg-surface hover:text-text-primary"
              )}
            >
              {it}
            </button>
          )
        )}
        <Button variant="ghost" size="icon" className="h-7 w-7" disabled={page >= pages} onClick={() => onPageChange(page + 1)} aria-label="Next">
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7" disabled={page >= pages} onClick={() => onPageChange(pages)} aria-label="Last">
          <ChevronsRight className="h-3.5 w-3.5" />
        </Button>
      </div>
      {onPageSizeChange && pages > 1 && (
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="h-7 rounded-md border border-border bg-bg-tertiary px-2 text-[11px] text-text-secondary outline-none"
        >
          {[10, 25, 50, 100].map((s) => (
            <option key={s} value={s}>{s}/page</option>
          ))}
        </select>
      )}
    </div>
  )
}