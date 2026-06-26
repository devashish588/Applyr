'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Rocket, Briefcase, Mail, ArrowRight,
  Building2, CalendarClock, ChevronRight,
} from 'lucide-react';
import Shell from '@/components/layout/Shell';
import ScoreRing from '@/components/ui/ScoreRing';
import ProgressBar from '@/components/ui/ProgressBar';
import { getAnalytics, getJobs, getStatus, getResumeParsed, getFollowupsDue, getStartups } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2, delay, ease: [0.16, 1, 0.3, 1] },
});

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [envStatus, setEnvStatus] = useState<any>(null);
  const [resumeData, setResumeData] = useState<any>(null);
  const [followupsDue, setFollowupsDue] = useState<any[]>([]);
  const [startups, setStartups] = useState<any[]>([]);

  const loadData = useCallback(() => {
    getAnalytics().then(r => setAnalytics(r.analytics)).catch(() => {});
    getJobs().then(r => setJobs((r.jobs || []).slice(0, 6))).catch(() => {});
    getStatus().then(setEnvStatus).catch(() => {});
    getFollowupsDue().then(r => setFollowupsDue(r.applications || [])).catch(() => {});
    getStartups(4).then(r => setStartups(r.startups || [])).catch(() => {});
    getResumeParsed().then(r => { if (r.success) setResumeData(r); }).catch(() => {});
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const a = analytics || {};
  const atsScore = resumeData?.health_json?.overall_score || 0;
  const hasJobs = (a.total_jobs || 0) > 0;

  return (
    <Shell>
      <div className="space-y-10">
        {/* ── Header ──────────────────────────────────────────────── */}
        <motion.div {...fadeUp(0)}>
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-page-title">Dashboard</h1>
              <p className="text-body mt-1">
                {hasJobs ? 'Your career pipeline at a glance.' : 'Run the pipeline to begin.'}
              </p>
            </div>
            <Link href="/pipeline" className="btn btn-primary btn-sm">
              <Rocket size={13} /> Run Pipeline
            </Link>
          </div>
        </motion.div>

        {/* ── Pipeline Stats — flat, no cards ─────────────────────── */}
        <motion.div {...fadeUp(0.02)}>
          <div className="text-label mb-4">Today's Pipeline</div>
          {hasJobs ? (
            <div className="grid grid-cols-4 gap-8">
              {[
                { label: 'Jobs Found', value: a.total_jobs ?? 0 },
                { label: 'Drafted', value: a.applications_drafted ?? 0 },
                { label: 'Submitted', value: a.applications_submitted ?? 0 },
                { label: 'Emails Sent', value: a.emails_sent ?? 0 },
              ].map(stat => (
                <div key={stat.label}>
                  <div className="text-2xl font-bold tabular-nums" style={{ color: 'var(--text)' }}>
                    {stat.value}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No pipeline runs yet.</p>
              <p className="text-xs mt-1.5" style={{ color: 'var(--text-faint)' }}>
                Expected first run: <span style={{ color: 'var(--text-secondary)' }}>120+ jobs</span> · <span style={{ color: 'var(--text-secondary)' }}>25 recruiters</span> · <span style={{ color: 'var(--text-secondary)' }}>15 tailored resumes</span> · ~2 min
              </p>
              <Link href="/pipeline" className="btn btn-sm btn-secondary mt-3">
                <Rocket size={12} /> Run first discovery
              </Link>
            </div>
          )}
        </motion.div>

        {/* ── Thin divider ────────────────────────────────────────── */}
        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* ── Readiness — flat inline row, no cards ───────────────── */}
        <motion.div {...fadeUp(0.04)}>
          <div className="text-label mb-4">System Readiness</div>
          <div className="flex items-center gap-8">
            {[
              { label: 'Resume', ready: envStatus?.resume_uploaded },
              { label: 'Email', ready: envStatus?.email?.configured },
              { label: 'Apollo', ready: envStatus?.recruiter_discovery?.apollo },
              { label: 'Pipeline', ready: true },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: item.ready ? 'var(--green)' : 'var(--amber)' }} />
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                <span className="text-xs" style={{ color: item.ready ? 'var(--green)' : 'var(--amber)' }}>
                  {item.ready ? 'Ready' : 'Needs setup'}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* ── Thin divider ────────────────────────────────────────── */}
        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* ── Top Matches + Follow-ups side by side ───────────────── */}
        <div className="grid grid-cols-[1fr_1fr] gap-12">
          {/* Top Matches */}
          <motion.div {...fadeUp(0.06)}>
            <div className="flex items-center justify-between mb-4">
              <div className="text-label">Top Matches</div>
              {jobs.length > 0 && (
                <Link href="/jobs" className="text-[11px]" style={{ color: 'var(--text-muted)' }}>View all →</Link>
              )}
            </div>
            {jobs.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No jobs discovered yet.</p>
            ) : (
              <div className="space-y-0">
                {jobs.map((job, i) => (
                  <div
                    key={`job-${job.id || i}`}
                    className="flex items-center justify-between py-2.5"
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {job.title || '—'}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {job.company || '—'}
                      </div>
                    </div>
                    {job.fit_score != null && (
                      <span className="text-xs font-bold tabular-nums ml-3"
                        style={{ color: job.fit_score >= 75 ? 'var(--green)' : job.fit_score >= 50 ? 'var(--amber)' : 'var(--text-muted)' }}>
                        {job.fit_score}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.div>

          {/* Follow-ups */}
          <motion.div {...fadeUp(0.07)}>
            <div className="flex items-center justify-between mb-4">
              <div className="text-label">Follow-ups Due</div>
              {followupsDue.length > 0 && (
                <span className="text-[10px] font-medium tabular-nums px-1.5 rounded-full" style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}>
                  {followupsDue.length}
                </span>
              )}
            </div>
            {followupsDue.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No follow-ups due. Apply to jobs to start tracking.</p>
            ) : (
              <div className="space-y-0">
                {followupsDue.slice(0, 5).map((item, i) => (
                  <div
                    key={`followup-${i}`}
                    className="flex items-center justify-between py-2.5"
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {item.company} · {item.role}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {formatDate(item.follow_up_date)}
                      </div>
                    </div>
                    <span className="badge badge-amber ml-2">Due</span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>

        {/* ── Companies — no cards, just a list ───────────────────── */}
        {startups.length > 0 && (
          <>
            <div style={{ borderTop: '1px solid var(--border)' }} />
            <motion.div {...fadeUp(0.08)}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-label">Matched Companies</div>
                <Link href="/startups" className="text-[11px]" style={{ color: 'var(--text-muted)' }}>View all →</Link>
              </div>
              <div className="grid grid-cols-4 gap-6">
                {startups.slice(0, 4).map((s, i) => (
                  <div key={`startup-${i}`}>
                    <div className="text-sm font-medium" style={{ color: 'var(--text)' }}>{s.company}</div>
                    <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      Score {s.overall_score} · {s.source}{s.is_remote ? ' · Remote' : ''}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </div>
    </Shell>
  );
}
