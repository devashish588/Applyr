import { useCallback, useMemo, useRef, useState } from "react"
import { Wand2, Upload, FileText, Shield, Zap, BookOpen, GraduationCap, Code, Sparkles } from "lucide-react"
import { motion } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { useResumeStatus, useParsedResume, useResumeSkills, useResumeExperience, useResumeEducation, useResumeHealth, useUploadResume } from "@/hooks/use-resume"
import { useJobs } from "@/hooks/use-jobs"
import { useAnalytics } from "@/hooks/use-dashboard"
import { Badge } from "@/components/ui"
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
    { label: "Resume Parsed", ok: !!health.resume_parsed, icon: FileText },
    { label: "Profile Generated", ok: !!health.profile_generated, icon: Shield },
    { label: "Embedding Created", ok: !!health.embedding_created, icon: Zap },
    { label: "Ready for Search", ok: !!health.ready_for_search, icon: Shield },
  ] : []

  const { data: jobs } = useJobs()
  useAnalytics()

  // Aggregate missing skills across all jobs → AI keyword suggestions
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
      <Topbar title="Resume Studio" icon={<Wand2 className="h-5 w-5" />} />
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-semibold">Resume</h2>
              <p className="text-[12px] text-text-muted">Manage your profile and skills</p>
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3.5 py-1.5 text-[12px] font-semibold text-text-primary transition hover:bg-surface-hover"
            >
              <Upload className="h-3.5 w-3.5" /> Upload
            </button>
            <input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.docx,.doc,.txt" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </div>

          {/* Upload zone when no resume */}
          {!status?.uploaded && (
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={cn(
                "mb-6 flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 text-center transition",
                isDragging ? "border-accent bg-accent-bg" : "border-border",
                uploadMutation.isPending && "pointer-events-none opacity-50"
              )}
            >
              <Upload className="h-10 w-10 text-text-muted" />
              <p className="text-sm font-medium text-text-primary">Drop your resume here</p>
              <p className="text-[12px] text-text-muted">PDF, DOCX, or TXT — max 50MB</p>
              {uploadMutation.isPending && <p className="text-[12px] text-accent-sub">Uploading & parsing…</p>}
              {uploadMutation.isError && <p className="text-[12px] text-red">Upload failed. Try again.</p>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Profile Card */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Profile</div>
              {resumeName ? (
                <div className="space-y-2">
                  <div><span className="text-[11px] text-text-muted">Name</span><div className="text-sm font-medium">{resumeName}</div></div>
                  {resumeEmail && <div><span className="text-[11px] text-text-muted">Email</span><div className="text-sm font-medium">{resumeEmail}</div></div>}
                  <div className="flex gap-4">
                    <div><span className="text-[11px] text-text-muted">Confidence</span><div className={cn("text-lg font-bold", confidence >= 70 ? "text-green" : confidence >= 50 ? "text-amber" : "text-red")}>{confidence}%</div></div>
                    {qualityScore > 0 && <div><span className="text-[11px] text-text-muted">Quality</span><div className="text-lg font-bold text-accent-sub">{qualityScore}</div></div>}
                  </div>
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">Upload a resume to see your profile</p>
              )}
            </div>

            {/* Health Card */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">Health</div>
              {healthItems.length > 0 ? (
                <div className="space-y-2">
                  {healthItems.map((h) => (
                    <div key={h.label} className="flex items-center gap-2.5">
                      <div className={cn("grid h-5 w-5 place-items-center rounded-full text-[9px]", h.ok ? "bg-green-bg text-green" : "bg-bg-tertiary text-text-muted")}>
                        {h.ok ? "✓" : "·"}
                      </div>
                      <span className="text-[12px] text-text-secondary">{h.label}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">No health data available</p>
              )}
            </div>

            {/* Skills Card */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                <Code className="h-3.5 w-3.5" /> Skills
              </div>
              {skills && skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {(skills as string[]).map((skill: string) => (
                    <span key={skill} className="rounded-md bg-accent-bg px-2 py-1 text-[11px] font-medium text-accent-sub">{skill}</span>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">No skills detected</p>
              )}
            </div>

            {/* AI Suggestions — missing keywords */}
            <div className="rounded-lg border border-accent/20 bg-accent/[0.02] p-5">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent-sub">
                  <Sparkles className="h-3.5 w-3.5" /> AI Suggestions
                </div>
                {missingSkills.length > 0 && (
                  <Badge variant="amber" status="dot">{missingSkills.length} keywords</Badge>
                )}
              </div>
              {missingSkills.length > 0 ? (
                <div className="space-y-2.5">
                  <p className="text-[11px] leading-relaxed text-text-secondary">
                    These keywords appear in your target roles but are missing from your resume. Adding them can improve your ATS match scores.
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {missingSkills.map(({ skill, n }) => (
                      <span
                        key={skill}
                        className="group inline-flex items-center gap-1 rounded-md border border-amber/20 bg-amber-bg px-2 py-1 text-[11px] font-medium text-amber"
                      >
                        {skill}
                        <span className="text-[9px] text-amber/60">{n}×</span>
                      </span>
                    ))}
                  </div>
                </div>
              ) : currentSkills.size > 0 ? (
                <p className="text-[12px] text-text-secondary">No missing keywords detected. Your resume covers the target roles.</p>
              ) : (
                <p className="text-[12px] text-text-muted">Upload a resume and run discovery to see AI suggestions.</p>
              )}
            </div>

            {/* Experience Card */}
            <div className="rounded-lg border border-border bg-surface p-5">
              <div className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                <BookOpen className="h-3.5 w-3.5" /> Experience
              </div>
              {experience && experience.length > 0 ? (
                <div className="space-y-3">
                  {experience.slice(0, 4).map((exp, i) => (
                    <div key={i}>
                      <div className="text-[13px] font-medium text-text-primary">{(exp as any).title || (exp as any).role || "Role"}</div>
                      <div className="text-[11px] text-text-muted">{(exp as any).company || ""} {(exp as any).duration ? `· ${(exp as any).duration}` : ""}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[12px] text-text-muted">No experience data</p>
              )}
            </div>

            {/* Education Card */}
            {education && education.length > 0 && (
              <div className="rounded-lg border border-border bg-surface p-5">
                <div className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  <GraduationCap className="h-3.5 w-3.5" /> Education
                </div>
                <div className="space-y-3">
                  {education.map((edu, i) => (
                    <div key={i}>
                      <div className="text-[13px] font-medium text-text-primary">{(edu as any).degree || (edu as any).qualification || "Degree"}</div>
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
