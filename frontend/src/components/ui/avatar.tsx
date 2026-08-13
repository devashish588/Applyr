import { cn } from "@/lib/utils"

interface AvatarProps {
  name: string | null | undefined
  size?: "xs" | "sm" | "md" | "lg"
  url?: string | null
  className?: string
}

const sizes = {
  xs: "h-5 w-5 text-[9px]",
  sm: "h-7 w-7 text-[11px]",
  md: "h-9 w-9 text-sm",
  lg: "h-12 w-12 text-base",
}

const gradients = [
  "bg-gradient-to-br from-accent to-teal-600",
  "bg-gradient-to-br from-blue to-indigo-600",
  "bg-gradient-to-br from-amber to-orange-600",
  "bg-gradient-to-br from-red to-pink-600",
  "bg-gradient-to-br from-purple-500 to-fuchsia-600",
]

export function Avatar({ name, size = "md", url, className }: AvatarProps) {
  const initials = (name || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase()

  const gradient = gradients[(name || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0) % gradients.length]

  if (url) {
    return <img src={url} alt={name || ""} className={cn("shrink-0 rounded-full object-cover", sizes[size], className)} />
  }

  return (
    <div
      className={cn(
        "shrink-0 grid place-items-center rounded-full font-bold text-white",
        gradient,
        sizes[size],
        className
      )}
    >
      {initials || "?"}
    </div>
  )
}