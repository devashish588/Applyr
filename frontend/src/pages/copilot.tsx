import { useState, useRef, useEffect } from "react"
import { Bot, Send, Sparkles, User, RefreshCw, Lightbulb, ChevronRight } from "lucide-react"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { FormattedText } from "@/components/ui/formatted-text"
import { askCopilot } from "@/api/copilot"

interface Message {
  id: string
  role: "user" | "copilot"
  content: string
  suggestions?: string[]
  action_type?: string
  timestamp: string
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      role: "copilot",
      content: "Hello! I am your Applyr Career Copilot. How can I assist with your job search strategy, resume tailoring, or recruiter outreach today?",
      suggestions: [
        "How can I improve my resume match score?",
        "What cold email template works best for recruiters?",
        "How should I prepare for a software engineering interview?"
      ],
      action_type: "greeting",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const handleSend = async (queryText?: string) => {
    const text = queryText || input
    if (!text.trim() || loading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setMessages((prev) => [...prev, userMsg])
    if (!queryText) setInput("")
    setLoading(true)

    try {
      const historyPayload = messages.slice(-4).map(m => ({ role: m.role, content: m.content }))
      const res = await askCopilot({ message: text, history: historyPayload })

      const copilotMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "copilot",
        content: res.message || "I've analyzed your question.",
        suggestions: res.suggestions || [],
        action_type: res.action_type || "advice",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages((prev) => [...prev, copilotMsg])
    } catch (err) {
      console.error(err)
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "copilot",
          content: "Sorry, I encountered an error connecting to the AI engine. Please verify your LLM API configuration in Settings.",
          suggestions: ["Check API status"],
          action_type: "error",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Topbar title="Career Copilot AI" icon={<Bot className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 flex flex-col p-6 max-w-5xl mx-auto w-full h-[calc(100vh-3.5rem)] space-y-4">

        {/* Main Chat Container */}
        <div className="flex-1 flex flex-col min-h-0 rounded-xl border border-border bg-bg-secondary overflow-hidden shadow-sm">
          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "copilot" && (
                  <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-accent/15 text-accent mt-0.5">
                    <Sparkles className="h-3.5 w-3.5" />
                  </div>
                )}
                <div className={`flex flex-col space-y-2 max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                  <div
                    className={`rounded-xl px-4 py-3 text-xs leading-relaxed ${
                      msg.role === "user"
                        ? "bg-accent text-white rounded-tr-none font-medium whitespace-pre-wrap"
                        : "bg-white/[0.02] text-text-primary border border-border/60 rounded-tl-none"
                    }`}
                  >
                    {msg.role === "user" ? msg.content : <FormattedText content={msg.content} />}
                  </div>

                  {/* Suggestion Pills */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {msg.suggestions.map((sug, i) => (
                        <button
                          key={i}
                          onClick={() => handleSend(sug)}
                          className="flex items-center gap-1.5 rounded-full border border-border/80 bg-white/[0.01] px-3 py-1 text-[11px] font-medium text-text-muted transition hover:border-accent/60 hover:text-text-primary hover:bg-white/[0.03]"
                        >
                          <Lightbulb className="h-3 w-3 text-amber shrink-0" />
                          <span>{sug}</span>
                          <ChevronRight className="h-3 w-3 text-text-faint" />
                        </button>
                      ))}
                    </div>
                  )}
                  <span className="text-[10px] text-text-faint px-1">{msg.timestamp}</span>
                </div>

                {msg.role === "user" && (
                  <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/[0.04] border border-border/60 text-text-secondary mt-0.5">
                    <User className="h-3.5 w-3.5" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 items-center text-text-muted text-xs">
                <div className="grid h-7 w-7 place-items-center rounded-lg bg-accent/15 text-accent">
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                </div>
                <span className="text-[11px] text-text-faint">Copilot is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="border-t border-border p-3 bg-black/20 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask Copilot about strategy, cold email wording, salary negotiation..."
              className="flex-1 rounded-lg border border-border bg-white/[0.02] px-3.5 py-2 text-xs text-text-primary placeholder:text-text-faint focus:border-accent/60 focus:ring-1 focus:ring-accent/15 outline-none transition"
            />
            <Button onClick={() => handleSend()} disabled={loading || !input.trim()} size="sm" className="h-9 text-xs gap-1.5">
              <Send className="h-3.5 w-3.5" />
              <span>Send</span>
            </Button>
          </div>
        </div>

      </div>
    </>
  )
}
