import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export interface Column<T> {
  key: string
  header: string
  align?: "left" | "center" | "right"
  width?: string
  render: (row: T, index: number) => ReactNode
}

interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  className?: string
  rowClassName?: (row: T, index: number) => string
  onRowClick?: (row: T) => void
  emptyState?: ReactNode
}

export function Table<T>({ columns, data, className, rowClassName, onRowClick, emptyState }: TableProps<T>) {
  if (data.length === 0 && emptyState) return <>{emptyState}</>

  return (
    <div className={cn("overflow-hidden rounded-lg border border-border bg-surface", className)}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-border bg-bg-secondary/60">
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={{ width: col.width }}
                  className={cn(
                    "px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center"
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick?.(row)}
                className={cn(
                  "transition-colors hover:bg-surface-hover",
                  i < data.length - 1 && "border-b border-border",
                  onRowClick && "cursor-pointer",
                  rowClassName?.(row, i)
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      "px-4 py-2.5 text-[13px]",
                      col.align === "right" && "text-right",
                      col.align === "center" && "text-center"
                    )}
                  >
                    {col.render(row, i)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}