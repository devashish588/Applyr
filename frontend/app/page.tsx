'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import Shell from '@/components/layout/Shell';
import CommandCenter from '@/components/dashboard/CommandCenter';
import AnimatedNumber from '@/components/ui/AnimatedNumber';
import {
  getAnalytics, getJobs, getStatus, getResumeParsed,
  getFollowupsDue, getStartups, getRecruiters,
} from '@/lib/api';
import { formatDate } from '@/lib/utils';

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2, delay, ease: EASE },
});

function SectionLabel({ children, href, action }: { children: React.ReactNode; href?: string; action?: string }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="text-label">{children}</div>
      {href && <Link href={href} className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{action || 'View all'} →</Link>}
    </div>
  );
}

// Dot-leader stat row: "Jobs Found ........ 124"
function StatRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-baseline">
      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span className="leader" />
      <AnimatedNumber value={value} className="text-sm font-semibold" style={{ color: 'var(--text)' }} />
    </div>
  );
}

function Divider() {
  return <div style={{ borderTop: '1px solid var(--border-subtle)' }} />;
}

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [envStatus, setEnvStatus] = useState<any>(null);
  const [resumeData, setResumeData] = useState<any>(null);
  const [followupsDue, setFollowupsDue] = useState<any[]>([]);
  const [startups, setStartups] = useState<any[]>([]);
  const [recruiters, setRecruiters] = useState<any[]>([]);

  const loadData = useCallback(() => {
    getAnalytics().then(r => setAnalytics(r.analytics)).catch(() => {});
    getJobs().then(r => setJobs(r.jobs || [])).catch(() => {});
    getStatus().then(setEnvStatus).catch(() => {});
    getFollowupsDue().then(r => setFollowupsDue(r.applications || [])).catch(() => {});
    getStartups(4).then(r => setStartups(r.startups || [])).catch(() => {});
    getRecruiters().then(r => setRecruiters(r.recruiters || [])).catch(() => {});
    getResumeParsed().then(r => { if (r.success) setResumeData(r); }).catch(() => {});
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const a = analytics || {};
  const topJobs = jobs.slice(0, 6);

  const stats = [
    { label: 'Jobs Found', value: a.total_jobs ?? 0 },
    { label: 'Recruiters', value: recruiters.length },
    { label: 'Applications', value: a.applications_drafted ?? 0 },
    { label: 'Emails', value: a.emails_sent ?? 0 },
  ];

  const readiness = [
    { label: 'Resume', ready: envStatus?.resume_uploaded },
    { label: 'Email', ready: envStatus?.email?.configured },
    { label: 'Apollo', ready: envStatus?.recruiter_discovery?.apollo },
    { label: 'Pipeline', ready: true },
  ];

  return (
    <Shell>
      <div className="space-y-12">
        {/* ── AI intro — pure typography, no box ──────────────────── */}
        <CommandCenter
          analytics={analytics}
          jobs={jobs}
          resumeData={resumeData}
          status={envStatus}
          followupsDue={followupsDue}
          recruiters={recruiters}
        />

        {/* ── Pipeline + Readiness — flat lists, side by side ─────── */}
        <motion.div {...fadeUp(0.02)} className="grid grid-cols-1 md:grid-cols-2 gap-x-16 gap-y-10">
          <div>
            <SectionLabel>Today's Pipeline</SectionLabel>
            <div className="space-y-3">
              {stats.map(s => <StatRow key={s.label} label={s.label} value={s.value} />)}
            </div>
          </div>

          <div>
            <SectionLabel>System Readiness</SectionLabel>
            <div className="space-y-3">
              {readiness.map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                  <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: item.ready ? 'var(--green)' : 'var(--amber)' }} />
                    <span className="text-xs" style={{ color: item.ready ? 'var(--green)' : 'var(--amber)' }}>
                      {item.ready ? 'Ready' : 'Needs setup'}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        <Divider />

        {/* ── Top Matches + Follow-ups — flat rows ────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-16 gap-y-10">
          <motion.div {...fadeUp(0.06)}>
            <SectionLabel href={topJobs.length > 0 ? '/jobs' : undefined}>Top Matches</SectionLabel>
            {topJobs.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No jobs discovered yet.</p>
            ) : (
              <div className="-mx-2">
                {topJobs.map((job, i) => {
                  const score = job.fit_score;
                  const color = score >= 75 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--text-muted)';
                  return (
                    <Link
                      key={`job-${job.id || i}`}
                      href="/jobs"
                      className="list-row flex items-center justify-between gap-3 px-2 py-2.5"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                          {job.title || '—'}
                        </div>
                        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                          {job.company || '—'}
                        </div>
                      </div>
                      {score != null && (
                        <span className="text-sm font-bold tabular-nums" style={{ color }}>{score}</span>
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </motion.div>

          <motion.div {...fadeUp(0.07)}>
            <SectionLabel>Follow-ups Due</SectionLabel>
            {followupsDue.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No follow-ups due. Apply to jobs to start tracking.</p>
            ) : (
              <div className="-mx-2">
                {followupsDue.slice(0, 6).map((item, i) => (
                  <div key={`followup-${i}`} className="list-row flex items-center justify-between gap-3 px-2 py-2.5">
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {item.company} · {item.role}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {formatDate(item.follow_up_date)}
                      </div>
                    </div>
                    <span className="text-xs" style={{ color: 'var(--amber)' }}>Due</span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>

        {/* ── Companies — flat list ───────────────────────────────── */}
        {startups.length > 0 && (
          <>
            <Divider />
            <motion.div {...fadeUp(0.08)}>
              <SectionLabel href="/startups">Matched Companies</SectionLabel>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-5">
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
