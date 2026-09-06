import { useState } from "react"
import { Link } from "react-router-dom"
import { Compass, Star, MapPin, ExternalLink } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Topbar } from "@/components/layout/topbar"
import { useJobs, useJobDetail } from "@/hooks/use-jobs"
import { runPipeline, pasteJD } from "@/api/pipeline"
import { cn, sanitizeCompany, scoreColor, scoreBgColor, scoreLabel, statusLabel, statusColor, truncate } from "@/lib/utils"
import type { Job, MatchDetails } from "@/types/api"

export default function DiscoverJobsPage() {
  const { data: jobs, isLoading } = useJobs()
  const [filter, setFilter] = useState<"best" | "all">("best")
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null)
  const { data: jobDetail } = useJobDetail(selectedJobId)

  const sorted = [...(jobs || [])].sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0))
  const filtered = filter === "best" ? sorted.filter((j) => (j.fit_score || 0) >= 70) : sorted
  const displayJobs = filtered.slice(0, 30)

  return (
    <>
      <Topbar title="Discover Jobs" icon={<Compass className="h-5 w-5" />} />
      <div className="flex flex-1 overflow-hidden">
        {/* Job list */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-semibold">Opportunity Feed</h2>
              <p className="text-[12px] text-text-muted">Best matches based on your profile</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-text-muted">{filtered.length} opportunities</span>
              <button
                onClick={() => setFilter("best")}
                className={cn("flex items-center gap-1 rounded-md px-2.5 py-1.5 text-[12px] font-medium transition", filter === "best" ? "border border-border bg-surface text-text-primary" : "text-text-secondary hover:bg-surface")}
              >
                <Star className="h-3.5 w-3.5" /> Best Matches
              </button>
              <button
                onClick={() => setFilter("all")}
                className={cn("rounded-md px-2.5 py-1.5 text-[12px] font-medium transition", filter === "all" ? "border border-border bg-surface text-text-primary" : "text-text-secondary hover:bg-surface")}
              >
                All
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 animate-shimmer rounded-lg" />)}
            </div>
          ) : displayJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-16 text-text-muted">
              <Compass className="h-8 w-8 opacity-20" />
              <p className="text-[13px]">No opportunities yet</p>
              <p className="text-[11px]">Click "Run Discovery" to find matching roles</p>
            </div>
          ) : (
            <div className="space-y-3">
              <AnimatePresence>
                {displayJobs.map((job, i) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    index={i}
                    isSelected={selectedJobId === job.id}
                    onSelect={() => setSelectedJobId(job.id)}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Detail panel */}
        <AnimatePresence>
          {selectedJobId && jobDetail && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 420, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="shrink-0 overflow-y-auto border-l border-border bg-bg-secondary"
            >
              <JobDetailPanel job={jobDetail.job} match={jobDetail.match} onClose={() => setSelectedJobId(null)} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}

function JobCard({ job, index, isSelected, onSelect }: { job: Job; index: number; isSelected: boolean; onSelect: () => void }) {
  const score = job.fit_score || 0
  const isBest = score >= 70
  let matchDetails: MatchDetails | null = null
  try { if (job.match_details_json) matchDetails = JSON.parse(job.match_details_json) } catch { /* ignore */ }
  const matchedSkills = matchDetails?.matched_skills || matchDetails?.skills_to_highlight || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.3 }}
      onClick={onSelect}
      className={cn(
        "flex cursor-pointer items-start gap-3.5 rounded-lg border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/15",
        isSelected ? "border-accent/30 bg-accent/[0.03]" : isBest ? "border-accent/20 bg-accent/[0.02]" : "border-border bg-surface",
        "hover:border-border-hover"
      )}
    >
      {/* Score */}
      <div className={cn("grid h-11 w-11 shrink-0 place-items-center rounded-lg text-base font-extrabold", scoreBgColor(score), scoreColor(score))}>
        {score}
      </div>

      {/* Body */}
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-semibold uppercase tracking-wider text-accent-sub">
          {sanitizeCompany(job.company)}
        </div>
        <div className="mt-0.5 text-[15px] font-semibold text-text-primary">{job.title || "Role"}</div>
        <div className="mt-1 flex items-center gap-2.5 text-[12px] text-text-muted">
          <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location || "Remote"}</span>
          <span>·</span>
          <span>{job.source || "web"}</span>
          {(job as any).freshness_state && (
            <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium", (job as any).freshness_state === "STALE" ? "bg-surface text-text-muted border border-border" : (job as any).freshness_state === "AGING" ? "bg-amber-bg text-amber" : (job as any).freshness_state === "NEW" ? "bg-accent-bg text-accent-sub" : "bg-surface text-text-muted")}>
              {(job as any).freshness_state}
            </span>
          )}
          {(job as any).is_duplicate && <span className="rounded border border-border px-1.5 py-0.5 text-[10px]">duplicate→{(job as any).canonical_job_id}</span>}
          {job.hr_email && <span className="rounded bg-green-bg px-1.5 py-0.5 text-[10px] font-medium text-green">Contact found</span>}
        </div>
        <div className="mt-2 flex gap-1">
          <Link to={`/jobs/${job.id}`} onClick={e=>e.stopPropagation()} className="rounded border border-border px-2 py-0.5 text-[10px] hover:bg-surface">View details →</Link>
          <Link to={`/studio/${job.id}`} onClick={e=>e.stopPropagation()} className="rounded bg-accent px-2 py-0.5 text-[10px] text-white">Prepare</Link>
        </div>
        {isBest && matchedSkills.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {matchedSkills.slice(0, 4).map((s) => (
              <span key={s} className="rounded bg-accent-bg px-1.5 py-0.5 text-[10px] font-medium text-accent-sub">✓ {s}</span>
            ))}
          </div>
        )}
        <div className="mt-2 flex items-center gap-2">
          <span className={cn("rounded px-2 py-0.5 text-[11px] font-medium", score >= 70 ? "bg-green-bg text-green" : score >= 50 ? "bg-amber-bg text-amber" : "bg-surface text-text-muted")}>
            {scoreLabel(score)}
          </span>
          <span className={cn("rounded px-2 py-0.5 text-[11px] font-medium", statusColor(job.status || "found"))}>
            {statusLabel(job.status || "found")}
          </span>
          <a href={`/studio/${job.id}`} onClick={(e)=>{e.stopPropagation()}} className="ml-auto rounded bg-accent px-2 py-0.5 text-[11px] font-medium text-white">Studio</a>
        </div>
      </div>
    </motion.div>
  )
}

function JobDetailPanel({ job, match, onClose }: { job: Job; match: MatchDetails | null; onClose: () => void }) {
  const [generating, setGenerating] = useState(false)
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState<'resume'|'cover'>('resume')
  const apiBase = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "")
  const assetHref = (p?: string) => {
    if (!p) return undefined
    if (p.startsWith("http://") || p.startsWith("https://")) return p
    const path = p.startsWith("/") ? p : `/${p}`
    return apiBase ? `${apiBase}${path}` : path
  }
  const filenameFrom = (p?: string) => (p ? p.split("/").pop() || 'file' : 'file')

  const startGeneratePackage = async () => {
    if (!job?.jd_text && !job?.title) return alert("No JD text available to generate package")
    setGenerating(true)
    try {
      await pasteJD(job.jd_text || job.title || "")
      alert("Package generation started — check Pipeline logs (Run History)")
    } catch (err) {
      console.error(err)
      alert("Failed to start package generation")
    } finally {
      setGenerating(false)
    }
  }

  const startRunFullPipeline = async () => {
    setRunning(true)
    try {
      const res = await runPipeline()
      alert(`Pipeline started (run id: ${res.run_id})`)
    } catch (err) {
      console.error(err)
      alert("Failed to start pipeline")
    } finally {
      setRunning(false)
    }
  }

  const jdText = (job.jd_text || (job as any).description || job.title || '').toString()
  const extractHighlights = (text: string) => {
    if (!text) return { keywords: [] as string[], sentences: [] as string[] }
    const stop = new Set(['the','and','or','a','an','to','for','with','of','in','on','that','as','is','are','be','by','at','from'])
    const tokens = text.toLowerCase().split(/[^a-z0-9+\-#_]+/).filter(Boolean)
    const freq: Record<string, number> = {}
    tokens.forEach(t => { if (!stop.has(t) && t.length>2) freq[t] = (freq[t]||0)+1 })
    const keywords = Object.entries(freq).sort((a,b)=>b[1]-a[1]).slice(0,8).map(e=>e[0])
    const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0,12)
    const highlighted = sentences.filter(s => keywords.some(k=>s.toLowerCase().includes(k))).slice(0,6)
    return { keywords, sentences: highlighted.length?highlighted:sentences.slice(0,6) }
  }
  const highlights = extractHighlights(jdText)

  return (
    <div className="w-[760px] p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="text-[12px] font-semibold uppercase tracking-wider text-accent-sub">{sanitizeCompany(job.company)}</div>
          <h2 className="mt-1 text-2xl font-semibold">{job.title}</h2>
          <div className="mt-2 flex items-center gap-3 text-[12px] text-text-muted">
            <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location || "Remote"}</span>
            <span className="rounded bg-surface px-2 py-0.5 text-[11px] font-medium">{job.source}</span>
            {job.url && (
              <a href={job.url} target="_blank" rel="noopener noreferrer" className="ml-2 inline-flex items-center gap-1 text-[12px] text-accent-sub hover:underline">
                <ExternalLink className="h-3 w-3" /> View Posting
              </a>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <select className="rounded-md border border-border bg-bg px-3 py-1 text-[13px] text-text-primary">
            <option>Devashish_June_July (default)</option>
          </select>
          <button onClick={startGeneratePackage} disabled={generating} className="rounded-md bg-purple-600 px-3 py-1 text-white text-sm disabled:opacity-60">{generating ? 'Generating…' : 'Generate Package'}</button>
          <button onClick={startRunFullPipeline} disabled={running} className="rounded-md bg-sky-600 px-3 py-1 text-white text-sm disabled:opacity-60">{running ? 'Starting…' : 'Run full pipeline'}</button>
          <button onClick={() => window.location.href = '/settings'} className="rounded-md border border-border px-2 py-1 text-[12px]">Edit templates</button>
          <button onClick={onClose} className="rounded-md p-1 text-text-muted transition hover:bg-surface hover:text-text-primary">✕</button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Left: Resume / Cover Letter */}
        <div className="flex-1">
          <div className="mb-3 flex gap-3">
            <button onClick={() => setTab('resume')} className={cn('flex-1 rounded-md px-4 py-2 font-semibold', tab==='resume' ? 'bg-surface/60' : 'border border-border')}>Resume</button>
            <button onClick={() => setTab('cover')} className={cn('flex-1 rounded-md px-4 py-2 font-semibold', tab==='cover' ? 'bg-surface/60' : 'border border-border')}>Cover Letter</button>
          </div>

          <div className="h-[420px] rounded-md border border-border bg-surface p-6 overflow-auto">
            {/* JD highlights */}
            <div className="mb-3">
              <div className="text-[12px] font-semibold text-text-muted">JD highlights</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {highlights.keywords.map(k => <span key={k} className="rounded px-2 py-1 text-sm border border-border">{k}</span>)}
              </div>
            </div>

            {tab === 'resume' ? (
              <div>
                {job.tailored_resume_path ? (
                  <div>
                    <div className="mb-3">Tailored resume available</div>
                    <a href={assetHref(`/api/jobs/${job.id}/asset/resume`)} target="_blank" rel="noopener noreferrer" download={filenameFrom(job.tailored_resume_path)} className="rounded-md bg-accent px-3 py-1 text-white">Download</a>
                  </div>
                ) : (
                  <div>
                    <div className="mb-3">No tailored resume yet.</div>
                    <div className="text-[13px] mb-4">Generate the application package to create tailored PDFs using the job description and your profile.</div>
                    <button onClick={startGeneratePackage} disabled={generating} className="rounded-md bg-purple-600 px-4 py-2 text-white">{generating ? 'Generating…' : 'Generate Package'}</button>
                  </div>
                )}
              </div>
            ) : (
              <div>
                {job.cover_letter_path ? (
                  <div>
                    <div className="mb-3">Cover letter available</div>
                    <a href={assetHref(`/api/jobs/${job.id}/asset/cover`)} target="_blank" rel="noopener noreferrer" download={filenameFrom(job.cover_letter_path)} className="rounded-md bg-accent px-3 py-1 text-white">Download cover letter</a>
                  </div>
                ) : (
                  <div>
                    <div className="mb-3">No cover letter generated yet.</div>
                    <div className="text-[13px] mb-3">Suggested short cover (copy & paste):</div>
                    <div className="rounded border border-border p-3 text-[13px] text-text-primary bg-surface">
                      <div style={{ marginBottom: 8 }}><strong>Dear Hiring Manager,</strong></div>
                      <div style={{ marginBottom: 8 }}>{match?.explanation || 'I am excited to apply for this role.'}</div>
                      <div style={{ marginBottom: 8 }}>Key fit: {(match?.skills_to_highlight || []).slice(0,4).join(', ')}</div>
                      <div>Best regards,</div>
                      <div>Your name</div>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => navigator.clipboard?.writeText((match?.explanation || '') + '\n\n' + ((match?.skills_to_highlight||[]).slice(0,4).join(', ')))} className="rounded-md border border-border px-3 py-2">Copy</button>
                      <button onClick={startGeneratePackage} disabled={generating} className="rounded-md bg-purple-600 px-3 py-2 text-white">Generate package</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Match + Outreach */}
        <aside className="w-80 space-y-4">
          {/* Signal / Score */}
          <div className="rounded-md border border-border bg-surface p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Signal score</div>
                <div className="mt-1 text-lg font-bold">{match ? Math.round(match.final_score || 0) : (job.fit_score || 0)}/100</div>
              </div>
              <div className="text-[12px] text-text-muted">{match?.recommendation || '—'}</div>
            </div>
            {match?.explanation && <p className="mt-3 text-[12px] text-text-secondary">{match.explanation}</p>}
          </div>

          {/* Proof Pack / Outreach */}
          <div className="rounded-md border border-border bg-surface p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Proof pack</div>
            <div className="mt-2 rounded-md bg-green-800/10 p-3 text-[13px]">Why I fit: {match?.skills_to_highlight?.slice(0,3).join(', ') || '—'}</div>
            <div className="mt-3 text-[12px] text-text-muted">Proof snippet</div>
            <div className="mt-2 text-[13px] text-text-secondary">{match?.why_this_score || job.title}</div>
          </div>

          <div className="rounded-md border border-border bg-surface p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Outreach Messages</div>
            <div className="mt-2 rounded-md bg-violet-900 p-3 text-white">3-line founder message<br/>{match?.explanation ? truncate(match.explanation, 90) : 'Quick message to start outreach'}</div>
            <div className="mt-3 text-[12px] text-text-muted">Cold email</div>
            <div className="mt-2 text-[13px] text-text-secondary">{job.email_subject || 'Subject: Relevant background'}</div>
          </div>

          {/* Follow-up presets */}
          <div className="rounded-md border border-border bg-surface p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">Follow-up</div>
            <div className="mt-2 flex gap-2">
              <button className="rounded-md bg-green-700 px-3 py-1 text-white text-sm">2 days</button>
              <button className="rounded-md bg-surface border border-border px-3 py-1 text-sm">5 days</button>
              <button className="rounded-md bg-surface border border-border px-3 py-1 text-sm">10 days</button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}