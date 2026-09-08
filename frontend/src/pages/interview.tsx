import { useState, useEffect } from "react"
import { useSearchParams, Link } from "react-router-dom"
import {
  GraduationCap, Sparkles, CheckCircle2, HelpCircle, Send, Award,
  AlertCircle, RefreshCw, BookOpen, ChevronRight, MessageSquare
} from "lucide-react"
import { Topbar } from "@/components/layout/topbar"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { fetchInterviewPrep as fetchGenericPrep, evaluateInterviewAnswer } from "@/api/interview"
import { fetchInterviewPrep as fetchAppPrep } from "@/api/interviews"
import type { InterviewPrepKit, InterviewEvaluation } from "@/types/api"
import { cn } from "@/lib/utils"

export default function InterviewPage() {
  const [searchParams] = useSearchParams()
  const appId = searchParams.get("appId")
  const [jobTitle, setJobTitle] = useState("Software Engineer")
  const [company, setCompany] = useState("Acme Corp")
  const [jdText, setJdText] = useState("")
  const [loadingPrep, setLoadingPrep] = useState(false)
  const [prepKit, setPrepKit] = useState<InterviewPrepKit | null>(null)

  // Interactive Answer Practice
  const [selectedQuestion, setSelectedQuestion] = useState("")
  const [userAnswer, setUserAnswer] = useState("")
  const [evaluating, setEvaluating] = useState(false)
  const [evaluation, setEvaluation] = useState<InterviewEvaluation | null>(null)

  useEffect(() => {
    if (appId) {
      setLoadingPrep(true)
      fetchAppPrep(Number(appId)).then(p => {
        const kit = (p as any)?.kit || p
        if (kit) setPrepKit(kit as any)
        const qs = (kit as any)?.likely_questions?.[0] || (kit as any)?.behavioral_questions?.[0]?.question
        if (qs) setSelectedQuestion(qs)
      }).catch(() => { }).finally(() => setLoadingPrep(false))
    }
  }, [appId])

  const handleGeneratePrep = async () => {
    setLoadingPrep(true)
    setEvaluation(null)
    try {
      if (appId) {
        const p = await fetchAppPrep(Number(appId))
        const kit = (p as any)?.kit || p
        if (kit) {
          setPrepKit(kit as any)
          const q = (kit as any)?.likely_questions?.[0] || (kit as any)?.behavioral_questions?.[0]?.question
          if (q) setSelectedQuestion(q)
        }
        return
      }
      const res = await fetchGenericPrep({
        title: jobTitle,
        company: company,
        jd_text: jdText,
      })
      if (res.success && res.prep) {
        setPrepKit(res.prep)
        if (res.prep.behavioral_questions.length > 0) {
          setSelectedQuestion(res.prep.behavioral_questions[0].question)
        }
      }
    } catch (err) {
      console.error("Failed to generate prep kit:", err)
    } finally {
      setLoadingPrep(false)
    }
  }

  const handleEvaluateAnswer = async () => {
    if (!selectedQuestion || !userAnswer.trim() || evaluating) return
    setEvaluating(true)
    try {
      const res = await evaluateInterviewAnswer({
        question: selectedQuestion,
        user_answer: userAnswer,
      })
      if (res.success && res.evaluation) {
        setEvaluation(res.evaluation)
      }
    } catch (err) {
      console.error("Failed to evaluate answer:", err)
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <>
      <Topbar title="AI Interview Intelligence" icon={<GraduationCap className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">

        {appId && (
          <div className="rounded-xl border border-accent/30 bg-accent/[0.03] p-4 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              <span>Tailored preparation active for <Link to={`/applications/${appId}`} className="font-semibold text-accent hover:underline">Application #{appId}</Link></span>
            </div>
            <span className="text-text-muted text-[11px]">Evidence & candidate skill gaps synchronized</span>
          </div>
        )}

        {/* Generator Inputs Header */}
        <Card className="rounded-xl border-border bg-bg-secondary">
          <CardHeader className="py-4">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
              <BookOpen className="h-3.5 w-3.5 text-accent" /> Interview Target Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-medium text-text-secondary mb-1 block">Target Role Title</label>
                <input
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer"
                  className="h-9 w-full rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none transition focus:border-accent/60 focus:ring-1 focus:ring-accent/15 placeholder:text-text-faint"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-text-secondary mb-1 block">Target Company</label>
                <input
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Stripe, Google, Acme Corp"
                  className="h-9 w-full rounded-lg border border-border bg-white/[0.02] px-3 text-xs text-text-primary outline-none transition focus:border-accent/60 focus:ring-1 focus:ring-accent/15 placeholder:text-text-faint"
                />
              </div>
            </div>
            <div>
              <label className="text-[11px] font-medium text-text-secondary mb-1 block">Job Description Snippet (Optional)</label>
              <textarea
                rows={2}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste key responsibilities or tech stack to generate tailored technical questions..."
                className="w-full rounded-lg border border-border bg-white/[0.02] p-3 text-xs text-text-primary outline-none transition focus:border-accent/60 focus:ring-1 focus:ring-accent/15 placeholder:text-text-faint"
              />
            </div>
            <div className="flex justify-end">
              <Button onClick={handleGeneratePrep} disabled={loadingPrep} className="h-8 text-xs font-medium gap-2">
                {loadingPrep ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                <span>Generate Interview Kit</span>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Generated Kit Display */}
        {prepKit ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Questions & Insights Column */}
            <div className="space-y-6">

              {/* Behavioral Questions */}
              <Card className="rounded-xl border-border">
                <CardHeader className="py-4">
                  <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                    <HelpCircle className="h-3.5 w-3.5 text-accent" /> Behavioral Questions (STAR Guidance)
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {prepKit.behavioral_questions.map((bq, idx) => {
                    const isSelected = selectedQuestion === bq.question
                    return (
                      <div
                        key={idx}
                        onClick={() => setSelectedQuestion(bq.question)}
                        className={cn(
                          "p-3.5 rounded-lg border cursor-pointer transition text-xs space-y-2",
                          isSelected
                            ? "border-accent/60 bg-accent/[0.04]"
                            : "border-border/60 bg-white/[0.01] hover:border-border hover:bg-white/[0.02]"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold text-accent tracking-wide uppercase">{bq.category}</span>
                          {isSelected && (
                            <span className="text-[10px] text-accent font-medium bg-accent/10 px-2 py-0.5 rounded-full">
                              Active Practice
                            </span>
                          )}
                        </div>
                        <p className="font-medium text-text-primary leading-snug">{bq.question}</p>
                        <p className="text-[11px] text-text-muted pt-2 border-t border-border/40 leading-relaxed">
                          <strong className="text-text-secondary font-medium">STAR Approach: </strong>
                          {bq.star_guidance}
                        </p>
                      </div>
                    )
                  })}
                </CardContent>
              </Card>

              {/* Technical Questions */}
              <Card className="rounded-xl border-border">
                <CardHeader className="py-4">
                  <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                    <Sparkles className="h-3.5 w-3.5 text-accent" /> Technical Drill-Down Questions
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {prepKit.technical_questions.map((tq, idx) => {
                    const isSelected = selectedQuestion === tq.question
                    return (
                      <div
                        key={idx}
                        onClick={() => setSelectedQuestion(tq.question)}
                        className={cn(
                          "p-3.5 rounded-lg border cursor-pointer transition text-xs space-y-2",
                          isSelected
                            ? "border-accent/60 bg-accent/[0.04]"
                            : "border-border/60 bg-white/[0.01] hover:border-border hover:bg-white/[0.02]"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold text-accent tracking-wide uppercase">{tq.topic}</span>
                        </div>
                        <p className="font-medium text-text-primary leading-snug">{tq.question}</p>
                        <p className="text-[11px] text-text-muted pt-2 border-t border-border/40 leading-relaxed">
                          <strong className="text-text-secondary font-medium">Key Answer Outline: </strong>
                          {tq.expected_answer_outline}
                        </p>
                      </div>
                    )
                  })}
                </CardContent>
              </Card>

              {/* Company Insights & Talking Points */}
              <Card className="rounded-xl border-border">
                <CardHeader className="py-4">
                  <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Company Intelligence & Points to Emphasize
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <p className="text-text-secondary leading-relaxed bg-white/[0.02] p-3 rounded-lg border border-border/60 text-[11px]">
                    {prepKit.company_insights}
                  </p>
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[11px] font-medium text-text-muted">Key Talking Points:</span>
                    {prepKit.talking_points.map((tp, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-[11px] text-text-secondary">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent mt-1.5 shrink-0" />
                        <span>{tp}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

            </div>

            {/* Practice Simulator Column */}
            <div className="space-y-6">
              <Card className="rounded-xl border-border">
                <CardHeader className="py-4">
                  <CardTitle className="text-xs font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                    <Award className="h-3.5 w-3.5 text-amber" /> Interactive Simulator & AI Evaluator
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-xs">
                  <div>
                    <label className="text-[11px] font-medium text-text-muted mb-1 block">Active Question</label>
                    <div className="p-3 rounded-lg bg-bg-secondary border border-border text-xs font-medium text-text-primary leading-snug">
                      {selectedQuestion || "Select a question from the left panel to begin practice."}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-medium text-text-muted mb-1 block">Your Response Practice</label>
                    <textarea
                      rows={6}
                      value={userAnswer}
                      onChange={(e) => setUserAnswer(e.target.value)}
                      placeholder="Type your response using Situation, Task, Action, and Result (STAR)..."
                      className="w-full rounded-lg border border-border bg-white/[0.02] p-3 text-xs text-text-primary outline-none transition focus:border-accent/60 focus:ring-1 focus:ring-accent/15 placeholder:text-text-faint"
                    />
                  </div>

                  <Button
                    onClick={handleEvaluateAnswer}
                    disabled={evaluating || !selectedQuestion || !userAnswer.trim()}
                    className="w-full h-9 text-xs font-medium gap-2"
                  >
                    {evaluating ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    <span>Evaluate Response with AI</span>
                  </Button>

                  {/* Feedback Display */}
                  {evaluation && (
                    <div className="space-y-3 pt-3 border-t border-border/60">
                      <div className="flex items-center justify-between bg-white/[0.02] p-3 rounded-lg border border-border/60">
                        <span className="text-xs font-medium text-text-muted">Answer Quality Score</span>
                        <span className={cn(
                          "text-base font-bold",
                          evaluation.score >= 75 ? "text-emerald-400" : evaluation.score >= 50 ? "text-amber" : "text-coral"
                        )}>
                          {evaluation.score} / 100
                        </span>
                      </div>

                      <div className="text-xs leading-relaxed text-text-secondary bg-bg-secondary p-3 rounded-lg border border-border/60">
                        <span className="font-medium text-accent block mb-1">AI Evaluation Feedback:</span>
                        {evaluation.feedback}
                      </div>

                      {evaluation.strengths && evaluation.strengths.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> Key Strengths
                          </span>
                          <ul className="list-disc list-inside text-[11px] text-text-muted space-y-0.5 pl-1">
                            {evaluation.strengths.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {evaluation.areas_for_improvement && evaluation.areas_for_improvement.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[11px] font-medium text-amber flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" /> Areas for Refinement
                          </span>
                          <ul className="list-disc list-inside text-[11px] text-text-muted space-y-0.5 pl-1">
                            {evaluation.areas_for_improvement.map((a, i) => (
                              <li key={i}>{a}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {evaluation.sample_improved_answer && (
                        <div className="p-3 rounded-lg bg-accent/[0.04] border border-accent/20 text-xs text-text-primary space-y-1">
                          <span className="font-medium text-accent block">Model High-Scoring Answer:</span>
                          <p className="italic text-text-secondary text-[11px] leading-relaxed">{evaluation.sample_improved_answer}</p>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

          </div>
        ) : (
          <div className="text-center py-12 border border-dashed border-border/60 rounded-xl">
            <GraduationCap className="h-8 w-8 text-text-faint mx-auto mb-2" />
            <h3 className="text-sm font-medium text-text-secondary">No Interview Kit Loaded</h3>
            <p className="text-xs text-text-faint max-w-sm mx-auto mt-1">Configure target role details above and click "Generate Interview Kit" to start practicing.</p>
          </div>
        )}

      </div>
    </>
  )
}
