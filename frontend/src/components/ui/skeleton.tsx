import { cn } from "@/lib/utils"

interface SkeletonProps {
  className?: string
  as?: keyof JSX.IntrinsicElements
  lines?: number
  width?: string
}

export function Skeleton({ className, lines = 1, width }: SkeletonProps) {
  if (lines > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="animate-shimmer rounded-md"
            style={{ height: "0.9em", width: width || (i === lines - 1 ? "60%" : "100%") }}
          />
        ))}
      </div>
    )
  }
  return <div className={cn("animate-shimmer rounded-md", className)} style={width ? { width } : undefined} />
}