import { useCallback, useMemo, useRef, useState } from "react"
import { Wand2, Upload, FileText, Shield, Zap, BookOpen, GraduationCap, Code, Sparkles, CheckCircle2 } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { useResumeStatus, useParsedResume, useResumeSkills, useResumeExperience, useResumeEducation, useResumeHealth, useUploadResume } from "@/hooks/use-resume"
import { useJobs } from "@/hooks/use-jobs"
import { useAnalytics } from "@/hooks/use-dashboard"
import { Button, Badge } from "@/components/ui"
import { cn } from "@/lib/utils"

export default function ResumeStudioPage() {
  const { data: status } = useResumeStatus()
  const { data: parsed } = useParsedResume()
  const { data: skills } = useResumeSkills()
  const { data: experience } = useResumeExperience()
  const { data: education } = useResumeEducation()
  const { data: health } = useResumeHealth()
  const uploadMutation = useUploadResume()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFile = useCallback((file: File) => {
    uploadMutation.mutate(file)
  }, [uploadMutation])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const pj = parsed?.parsed_json as Record<string, unknown> | undefined
  const resumeName = (pj?.name || pj?.full_name || "") as string
  const resumeEmail = (pj?.email || "") as string
  const confidence = parsed?.parse_status === "success" ? ((pj?.confidence as number) || 0) : 0
  const qualityScore = (pj?.quality_score as number) || 0

  const healthItems = health ? [
    { label: "Resume Document Parsed", ok: !!health.resume_parsed, icon: FileText },
    { label: "Candidate Profile Built", ok: !!health.profile_generated, icon: Shield },
    { label: "Vector Embedding Created", ok: !!health.embedding_created, icon: Zap },
    { label: "Match Search Engine Ready", ok: !!health.ready_for_search, icon: Shield },
  ] : []

  const { data: jobs } = useJobs()
  useAnalytics()

  const missingSkills = useMemo(() => {
    const count: Record<string, number> = {}
    for (const job of jobs || []) {
      if (!job.match_details_json) continue
      try {
        const m = JSON.parse(job.match_details_json)
        const missing = m.missing_skills || m.missing_requirements || []
        for (const s of missing) {
          count[s] = (count[s] || 0) + 1
        }
      } catch { /* ignore */ }
    }
    return Object.entries(count)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([skill, n]) => ({ skill, n }))
  }, [jobs])

  const currentSkills = useMemo(() => new Set((skills as string[]) || []), [skills])

  return (
    <>
      <Topbar title="Resume Intelligence Studio" icon={<Wand2 className="h-4 w-4 text-text-muted" />} />
      <div className="flex-1 overflow-y-auto p-6 max-w-6xl mx-auto space-y-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>

          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-text-primary tracking-tight">Base Resume Profile</h2>
              <p className="text-xs text-text-muted">Master candidate evidence, extracted skills, and vector embeddings</p>
            </div>
            <Button
              onClick={() => fileInputRef.current?.click()}
              size="sm"
              className="h-8 text-xs gap-1.5"
            >
              <Upload className="h-3.5 w-3.5" /> Upload Resume
            </Button>
            <input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </div>

          {/* Upload Zone */}
          {!status?.uploaded && (
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={cn(
                "mb-6 flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-10 text-center transition",
                isDragging ? "border-accent bg-accent/[0.04]" : "border-border/80 bg-bg-secondary",
                uploadMutation.isPending && "pointer-events-none opacity-50"
              )}
            >
              <Upload className="h-8 w-8 text-text-faint" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-text-primary">Drag & drop your primary resume here</p>
                <p className="text-xs text-text-muted">Supports PDF, DOCX, or TXT — maximum 50MB</p>
              </div>
              {uploadMutation.isPending && <p className="text-xs text-accent font-medium">Parsing resume & generating candidate profile…</p>}
              {uploadMutation.isError && <p className="text-xs text-coral">Upload failed. Please check file format.</p>}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Profile Card */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Candidate Identity & Parsing Quality</div>
              {resumeName ? (
                <div className="space-y-3 pt-1 text-xs">
                  <div>
                    <span className="text-[11px] text-text-muted block">Full Name</span>
                    <div className="text-sm font-semibold text-text-primary mt-0.5">{resumeName}</div>
                  </div>
                  {resumeEmail && (
                    <div>
                      <span className="text-[11px] text-text-muted block">Primary Email</span>
                      <div className="text-xs font-mono text-text-secondary mt-0.5">{resumeEmail}</div>
                    </div>
                  )}
                  <div className="flex gap-6 pt-2 border-t border-border/40">
                    <div>
                      <span className="text-[11px] text-text-muted block">Parsing Confidence</span>
                      <div className={cn("text-base font-bold font-mono mt-0.5", confidence >= 70 ? "text-emerald-400" : confidence >= 50 ? "text-amber" : "text-coral")}>
                        {confidence}%
                      </div>
                    </div>
                    {qualityScore > 0 && (
                      <div>
                        <span className="text-[11px] text-text-muted block">Profile Quality Score</span>
                        <div className="text-base font-bold font-mono text-accent mt-0.5">{qualityScore}</div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-text-faint">Upload a resume document to generate your profile.</p>
              )}
            </div>

            {/* Health Card */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">Engine Readiness Health</div>
              {healthItems.length > 0 ? (
                <div className="space-y-2.5 pt-1">
                  {healthItems.map((h) => (
                    <div key={h.label} className="flex items-center gap-3 text-xs">
                      <div className={cn("grid h-5 w-5 place-items-center rounded-full text-[10px] shrink-0 font-bold", h.ok ? "bg-emerald-500/10 text-emerald-400" : "bg-white/[0.04] text-text-faint")}>
                        {h.ok ? "✓" : "·"}
                      </div>
                      <span className="text-text-secondary">{h.label}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-faint">No health telemetry available.</p>
              )}
            </div>

            {/* Skills Card */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Code className="h-3.5 w-3.5 text-accent" /> Extracted Candidate Skills ({skills?.length || 0})
              </div>
              {skills && skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {(skills as string[]).map((skill: string) => (
                    <span key={skill} className="rounded-md bg-white/[0.03] border border-border/60 px-2.5 py-1 text-[11px] font-medium text-text-secondary">
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-faint">No skills extracted yet.</p>
              )}
            </div>

            {/* AI Keyword Suggestions */}
            <div className="rounded-xl border border-accent/30 bg-accent/[0.02] p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-accent flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5" /> High-Value ATS Keyword Recommendations
                </div>
                {missingSkills.length > 0 && (
                  <Badge variant="amber">{missingSkills.length} High-Impact</Badge>
                )}
              </div>
              {missingSkills.length > 0 ? (
                <div className="space-y-3 text-xs">
                  <p className="text-text-muted text-[11px] leading-relaxed">
                    These skills frequently appear in high-match target roles but are missing from your base resume profile:
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {missingSkills.map(({ skill, n }) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1.5 rounded-md border border-amber/30 bg-amber/5 px-2.5 py-1 text-[11px] font-medium text-amber"
                      >
                        {skill}
                        <span className="text-[9px] opacity-70 font-mono">({n}x)</span>
                      </span>
                    ))}
                  </div>
                </div>
              ) : currentSkills.size > 0 ? (
                <p className="text-xs text-text-muted pt-1">Your base resume currently covers all target role keywords!</p>
              ) : (
                <p className="text-xs text-text-faint pt-1">Upload a resume and discover jobs to see keyword recommendations.</p>
              )}
            </div>

            {/* Experience Card */}
            <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
              <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                <BookOpen className="h-3.5 w-3.5 text-accent" /> Work Experience Highlights
              </div>
              {experience && experience.length > 0 ? (
                <div className="space-y-3 pt-1">
                  {experience.slice(0, 4).map((exp, i) => (
                    <div key={i} className="text-xs space-y-0.5 border-b border-border/40 pb-2 last:border-0 last:pb-0">
                      <div className="font-semibold text-text-primary">{(exp as any).title || (exp as any).role || "Role"}</div>
                      <div className="text-[11px] text-text-muted">{(exp as any).company || ""} {(exp as any).duration ? `· ${(exp as any).duration}` : ""}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-faint">No work experience parsed.</p>
              )}
            </div>

            {/* Education Card */}
            {education && education.length > 0 && (
              <div className="rounded-xl border border-border bg-bg-secondary p-5 space-y-4">
                <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <GraduationCap className="h-3.5 w-3.5 text-accent" /> Education & Credentials
                </div>
                <div className="space-y-3 pt-1">
                  {education.map((edu, i) => (
                    <div key={i} className="text-xs space-y-0.5">
                      <div className="font-semibold text-text-primary">{(edu as any).degree || (edu as any).qualification || "Degree"}</div>
                      <div className="text-[11px] text-text-muted">{(edu as any).institution || (edu as any).school || ""}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </motion.div>
      </div>
    </>
  )
}
