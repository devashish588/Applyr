import { cn } from "@/lib/utils"

interface LogoProps {
  className?: string
  size?: "sm" | "md" | "lg"
  showWordmark?: boolean
}

export function ApplyrLogo({ className, size = "md", showWordmark = false }: LogoProps) {
  const dim = size === "sm" ? "h-6 w-6" : size === "lg" ? "h-8 w-8" : "h-7 w-7"

  return (
    <div className={cn("inline-flex items-center gap-2.5 select-none", className)}>
      <svg
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn("shrink-0 transition-transform duration-200 hover:scale-105", dim)}
      >
        {/* Sleek rounded squircle surface matching #11151A with #242A32 border */}
        <rect width="32" height="32" rx="8" fill="#11151A" stroke="#242A32" strokeWidth="1" />
        
        {/* Minimal geometric chevron 'A' delta mark in electric blue #5B8CFF */}
        <path
          d="M16 6.5L24.5 23H20.2L16 14.2L11.8 23H7.5L16 6.5Z"
          fill="#5B8CFF"
        />

        {/* Minimal horizontal crossbar accent */}
        <rect x="12" y="18" width="8" height="2" rx="1" fill="#0B0D10" />
        
        {/* Subtle active status pulse dot in emerald #22C55E */}
        <circle cx="23" cy="8" r="1.75" fill="#22C55E" />
      </svg>

      {showWordmark && (
        <span className="text-[15px] font-semibold tracking-tight text-text-primary">
          Applyr
        </span>
      )}
    </div>
  )
}
