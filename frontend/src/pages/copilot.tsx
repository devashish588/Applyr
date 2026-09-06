import { useState, useRef, useEffect } from "react"
import { Bot, Send, Sparkles, User, RefreshCw, Lightbulb, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
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
      content: "Hello! I am your **Applyr 2.0 Career Copilot**. How can I help with your job search strategy, resume tailoring, or outreach today?",
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
    <div className="flex h-full flex-col p-6 space-y-4 max-w-5xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-accent to-teal-600 text-white shadow-md">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary flex items-center gap-2">
              Career Copilot
              <span className="rounded-full bg-accent-bg px-2 py-0.5 text-[11px] font-semibold text-accent-sub">
                AI Assistant
              </span>
            </h1>
            <p className="text-xs text-text-secondary">
              Real-time advice, resume suggestions & job search strategy
            </p>
          </div>
        </div>
      </div>

      {/* Main Chat Box */}
      <Card className="flex-1 flex flex-col min-h-0 bg-surface border-border overflow-hidden">
        <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "copilot" && (
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/20 text-accent">
                  <Sparkles className="h-4 w-4" />
                </div>
              )}
              <div className={`flex flex-col space-y-2 max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div
                  className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-accent text-white rounded-br-none"
                      : "bg-bg-secondary text-text-primary border border-border rounded-bl-none"
                  }`}
                >
                  {msg.content}
                </div>

                {/* Suggestions Pills */}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {msg.suggestions.map((sug, i) => (
                      <button
                        key={i}
                        onClick={() => handleSend(sug)}
                        className="flex items-center gap-1 rounded-full border border-border bg-bg-tertiary px-3 py-1 text-[11px] font-medium text-text-secondary transition hover:border-accent hover:text-accent"
                      >
                        <Lightbulb className="h-3 w-3 text-amber-400" />
                        <span>{sug}</span>
                        <ChevronRight className="h-3 w-3 opacity-60" />
                      </button>
                    ))}
                  </div>
                )}
                <span className="text-[10px] text-text-muted px-1">{msg.timestamp}</span>
              </div>

              {msg.role === "user" && (
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-bg-tertiary text-text-secondary">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 items-center text-text-muted text-xs">
              <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent/20 text-accent">
                <RefreshCw className="h-4 w-4 animate-spin" />
              </div>
              <span>Copilot is analyzing your question...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </CardContent>

        {/* Input Bar */}
        <div className="border-t border-border p-3 bg-bg-secondary flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask Copilot about strategy, cold email wording, salary negotiation..."
            className="flex-1 rounded-lg border border-border bg-surface px-3.5 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
          />
          <Button onClick={() => handleSend()} disabled={loading || !input.trim()} className="gap-2">
            <Send className="h-4 w-4" />
            <span>Send</span>
          </Button>
        </div>
      </Card>
    </div>
  )
}
