import React from "react"
import { cn } from "@/lib/utils"

interface FormattedTextProps {
  content?: string | null
  className?: string
}

/** Clean conversational filler from AI text start/end */
export function cleanAIFiller(text: string): string {
  if (!text || typeof text !== "string") return ""
  let cleaned = text.trim()
  
  // Remove starting "Here is a strategic framework:", "Great question!", etc.
  cleaned = cleaned.replace(/^(great question!|sure!|absolutely!|here is a strategic framework:?|here is the framework:?)\s*/i, "")
  // Remove ending "Hope this helps!", etc.
  cleaned = cleaned.replace(/\s*(hope this helps!?|let me know if you need anything else!?)$/i, "")

  // Remove "Here is a strategic framework:" embedded before lists
  cleaned = cleaned.replace(/\n\s*here is a strategic framework:\s*\n/gi, "\n\n")

  return cleaned.trim()
}

/** Parses inline markdown like **bold** into React nodes safely */
export function parseInline(text: string): React.ReactNode[] {
  if (!text || typeof text !== "string") return []
  
  const parts = text.split(/(\*\*|__)/)
  const nodes: React.ReactNode[] = []
  let isBold = false

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    if (part === "**" || part === "__") {
      isBold = !isBold
    } else if (part) {
      if (isBold) {
        nodes.push(
          <strong key={i} className="font-semibold text-text-primary">
            {part}
          </strong>
        )
      } else {
        nodes.push(part)
      }
    }
  }

  return nodes
}

/** Words that indicate a normal prose sentence rather than a section title */
const PROSE_VERBS_REGEX = /\b(requires|includes|matters|contains|focuses|provides|covers|shows|is|are|was|were|be|been|have|has|had|can|should|will|would|could|for|with|about|into)\b/i

/** Conservative detection for short standalone section titles like "CORE LANGUAGES:" */
export function isStandaloneSectionHeading(line: string): boolean {
  if (!line || !line.endsWith(":") || line.length > 30) return false
  
  // If line contains punctuation like comma, dot, question mark -> prose sentence
  if (/[.,?!=]/.test(line.slice(0, -1))) return false

  // If line contains common sentence/prose verbs or prepositions -> prose sentence
  if (PROSE_VERBS_REGEX.test(line)) return false

  // Must be uppercase (CORE LANGUAGES:) or Title Case without sentence structure
  const rawTitle = line.slice(0, -1).trim()
  if (!rawTitle) return false

  const isAllUpper = rawTitle === rawTitle.toUpperCase() && /[A-Z]/.test(rawTitle)
  const isTitleCase = rawTitle.split(/\s+/).every(word => /^[A-Z][a-z0-9]*$/.test(word))

  return isAllUpper || isTitleCase
}

export function FormattedText({ content, className }: FormattedTextProps) {
  if (!content || typeof content !== "string") return null

  const cleaned = cleanAIFiller(content)
  if (!cleaned) return null

  const lines = cleaned.split("\n")

  const blocks: React.ReactNode[] = []
  let currentList: { type: "ul" | "ol"; items: string[] } | null = null

  const flushList = (keyPrefix: number) => {
    if (!currentList) return
    const ListTag = currentList.type === "ul" ? "ul" : "ol"
    const isUl = currentList.type === "ul"

    blocks.push(
      <ListTag
        key={`list-${keyPrefix}`}
        className={cn(
          "my-2 space-y-1.5 pl-4 text-xs text-text-secondary",
          isUl ? "list-disc" : "list-decimal"
        )}
      >
        {currentList.items.map((item, idx) => (
          <li key={idx} className="leading-relaxed">
            {parseInline(item)}
          </li>
        ))}
      </ListTag>
    )
    currentList = null
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()

    if (!line) {
      flushList(i)
      continue
    }

    // Check bullet list item (* or - or +)
    const bulletMatch = line.match(/^[*+\-]\s+(.+)/)
    if (bulletMatch) {
      if (currentList && currentList.type !== "ul") {
        flushList(i)
      }
      if (!currentList) {
        currentList = { type: "ul", items: [] }
      }
      currentList.items.push(bulletMatch[1])
      continue
    }

    // Check numbered list item (1. or 2.)
    const numberMatch = line.match(/^\d+[\.\)]\s+(.+)/)
    if (numberMatch) {
      if (currentList && currentList.type !== "ol") {
        flushList(i)
      }
      if (!currentList) {
        currentList = { type: "ol", items: [] }
      }
      currentList.items.push(numberMatch[1])
      continue
    }

    // If we reach a non-list line, flush pending list
    flushList(i)

    // Check explicit Markdown heading (# ## ### ####)
    const headingMatch = line.match(/^(#{1,4})\s+(.+)/)
    if (headingMatch) {
      const headingText = headingMatch[2]
      blocks.push(
        <h4
          key={`h-${i}`}
          className="mt-3 mb-1 text-[11px] font-semibold tracking-wider text-text-primary border-b border-border/40 pb-0.5"
        >
          {parseInline(headingText)}
        </h4>
      )
      continue
    }

    // Check conservative standalone section header (e.g. "CORE LANGUAGES:")
    if (isStandaloneSectionHeading(line)) {
      const title = line.slice(0, -1).trim()
      blocks.push(
        <h4
          key={`sh-${i}`}
          className="mt-3 mb-1 text-[11px] font-semibold uppercase tracking-wider text-accent"
        >
          {parseInline(title)}
        </h4>
      )
      continue
    }

    // Regular paragraph fallback
    blocks.push(
      <p key={`p-${i}`} className="mb-2 leading-relaxed text-xs text-text-primary">
        {parseInline(line)}
      </p>
    )
  }

  flushList(lines.length)

  return <div className={cn("space-y-1", className)}>{blocks}</div>
}
