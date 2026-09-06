import { useState, useEffect } from "react"
import { useSearchParams, Link } from "react-router-dom"
import { GraduationCap, Sparkles, CheckCircle2, HelpCircle, Send, Award, AlertCircle, RefreshCw, BookOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { fetchInterviewPrep as fetchGenericPrep, evaluateInterviewAnswer } from "@/api/interview"
import { fetchInterviewPrep as fetchAppPrep } from "@/api/interviews"
import type { InterviewPrepKit, InterviewEvaluation } from "@/types/api"

export default function InterviewPage() {
  const [searchParams] = useSearchParams()
  const appId = searchParams.get("appId")
  const [jobTitle, setJobTitle] = useState("Software Engineer")
  const [company, setCompany] = useState("Acme Corp")
  const [jdText, setJdText] = useState("")
  const [loadingPrep, setLoadingPrep] = useState(false)
  const [prepKit, setPrepKit] = useState<InterviewPrepKit | null>(null)

  useEffect(() => {
    if (appId) {
      setLoadingPrep(true)
      fetchAppPrep(Number(appId)).then(p => {
        // p may be {kit} or prep directly
        const kit = (p as any)?.kit || p
        if (kit) setPrepKit(kit as any)
        const qs = (kit as any)?.likely_questions?.[0] || (kit as any)?.behavioral_questions?.[0]?.question
        if (qs) setSelectedQuestion(qs)
      }).catch(()=>{}).finally(()=>setLoadingPrep(false))
    }
  }, [appId])

  // Interactive Answer Practice
  const [selectedQuestion, setSelectedQuestion] = useState("")
  const [userAnswer, setUserAnswer] = useState("")
  const [evaluating, setEvaluating] = useState(false)
  const [evaluation, setEvaluation] = useState<InterviewEvaluation | null>(null)

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
    <div className="flex h-full flex-col p-6 space-y-6 overflow-y-auto max-w-6xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary flex items-center gap-2">
              AI Interview Prep
              <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-[11px] font-semibold text-indigo-400">
                Applyr 2.0
              </span>
            </h1>
            <p className="text-xs text-text-secondary">
              Generate job-specific practice questions, STAR answer guidelines & live feedback
            </p>
          </div>
        </div>
      </div>

      {appId && (
        <div className="rounded border border-accent bg-accent-bg p-3 text-sm">
          Showing prep for <Link to={`/applications/${appId}`} className="font-medium text-accent underline">Application #{appId}</Link> — <span className="text-text-muted">candidate evidence and gaps linked</span>
        </div>
      )}

      {/* Generator Inputs */}
      <Card className="bg-surface border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium flex items-center gap-2 text-text-primary">
            <BookOpen className="h-4 w-4 text-indigo-400" />
            Interview Target Setup
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Target Role Title</label>
              <input
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Senior Backend Engineer"
                className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-text-secondary mb-1 block">Target Company</label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Stripe, Google, Acme Corp"
                className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-text-secondary mb-1 block">Job Description Snippet (Optional)</label>
            <textarea
              rows={2}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste job description requirements or responsibilities to customize technical questions..."
              className="w-full rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none"
            />
          </div>
          <Button onClick={handleGeneratePrep} disabled={loadingPrep} className="gap-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:opacity-90">
            {loadingPrep ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            <span>Generate Interview Kit</span>
          </Button>
        </CardContent>
      </Card>

      {/* Generated Kit Display */}
      {prepKit && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Questions & Insights Column */}
          <div className="space-y-4">
            {/* Behavioral Questions */}
            <Card className="bg-surface border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <HelpCircle className="h-4 w-4 text-purple-400" />
                  Behavioral Questions (STAR Method)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {prepKit.behavioral_questions.map((bq, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedQuestion(bq.question)}
                    className={`p-3 rounded-lg border cursor-pointer transition ${
                      selectedQuestion === bq.question
                        ? "border-indigo-500 bg-indigo-500/10"
                        : "border-border bg-bg-secondary hover:border-text-muted"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">{bq.category}</span>
                      {selectedQuestion === bq.question && <span className="text-[10px] bg-indigo-500 text-white px-2 py-0.5 rounded-full font-medium">Selected</span>}
                    </div>
                    <p className="text-sm font-medium text-text-primary mt-1">{bq.question}</p>
                    <p className="text-xs text-text-secondary mt-2 border-t border-border/50 pt-2">
                      <span className="font-semibold text-accent-sub">STAR Guidance:</span> {bq.star_guidance}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Technical Questions */}
            <Card className="bg-surface border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-accent" />
                  Technical Drill-Down Questions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {prepKit.technical_questions.map((tq, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedQuestion(tq.question)}
                    className={`p-3 rounded-lg border cursor-pointer transition ${
                      selectedQuestion === tq.question
                        ? "border-indigo-500 bg-indigo-500/10"
                        : "border-border bg-bg-secondary hover:border-text-muted"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-accent uppercase tracking-wider">{tq.topic}</span>
                    </div>
                    <p className="text-sm font-medium text-text-primary mt-1">{tq.question}</p>
                    <p className="text-xs text-text-secondary mt-2 border-t border-border/50 pt-2">
                      <span className="font-semibold text-text-muted">Expected Key Outline:</span> {tq.expected_answer_outline}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Company Insights */}
            <Card className="bg-surface border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green" />
                  Company Culture & Talking Points
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-text-secondary leading-relaxed bg-bg-tertiary p-3 rounded-lg border border-border">
                  {prepKit.company_insights}
                </p>
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold text-text-muted">Resume Points to Emphasize:</span>
                  {prepKit.talking_points.map((tp, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-text-primary">
                      <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                      <span>{tp}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Interactive Practice & Evaluator Column */}
          <div className="space-y-4">
            <Card className="bg-surface border-border">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-text-primary flex items-center gap-2">
                  <Award className="h-4 w-4 text-amber-400" />
                  Practice Simulator & Answer Evaluator
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">Selected Question</label>
                  <div className="p-3 rounded-lg bg-bg-tertiary border border-border text-sm font-medium text-text-primary">
                    {selectedQuestion || "Click a question on the left to practice!"}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">Your Practice Answer</label>
                  <textarea
                    rows={6}
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    placeholder="Type your practice response here using Situation, Task, Action, Result..."
                    className="w-full rounded-lg border border-border bg-bg-secondary p-3 text-sm text-text-primary placeholder:text-text-muted focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <Button
                  onClick={handleEvaluateAnswer}
                  disabled={evaluating || !selectedQuestion || !userAnswer.trim()}
                  className="w-full gap-2 bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  {evaluating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  <span>Evaluate My Response</span>
                </Button>

                {/* Feedback Output */}
                {evaluation && (
                  <div className="space-y-3 pt-3 border-t border-border">
                    <div className="flex items-center justify-between bg-bg-tertiary p-3 rounded-lg border border-border">
                      <span className="text-xs font-semibold text-text-secondary">Answer Score</span>
                      <span className={`text-lg font-bold ${evaluation.score >= 75 ? "text-green" : evaluation.score >= 50 ? "text-amber-400" : "text-red"}`}>
                        {evaluation.score} / 100
                      </span>
                    </div>

                    <div className="text-xs leading-relaxed text-text-primary bg-bg-secondary p-3 rounded-lg border border-border">
                      <span className="font-semibold text-indigo-400 block mb-1">Feedback:</span>
                      {evaluation.feedback}
                    </div>

                    {evaluation.strengths && evaluation.strengths.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-green flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Strengths
                        </span>
                        <ul className="list-disc list-inside text-xs text-text-secondary space-y-0.5 pl-1">
                          {evaluation.strengths.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {evaluation.areas_for_improvement && evaluation.areas_for_improvement.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-semibold text-amber-400 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" /> Areas for Improvement
                        </span>
                        <ul className="list-disc list-inside text-xs text-text-secondary space-y-0.5 pl-1">
                          {evaluation.areas_for_improvement.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {evaluation.sample_improved_answer && (
                      <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-xs text-text-primary space-y-1">
                        <span className="font-semibold text-indigo-400 block">Sample High-Scoring Model Answer:</span>
                        <p className="italic text-text-secondary">{evaluation.sample_improved_answer}</p>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
