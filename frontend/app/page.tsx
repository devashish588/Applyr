'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import Shell from '@/components/layout/Shell';
import CommandCenter from '@/components/dashboard/CommandCenter';
import MetricCard from '@/components/ui/MetricCard';
import {
  getAnalytics, getJobs, getStatus, getResumeParsed,
  getFollowupsDue, getStartups, getRecruiters,
} from '@/lib/api';
import { formatDate } from '@/lib/utils';
import {
  Briefcase, Users, FileText, Mail,
  CheckCircle2, AlertCircle, Building2, ArrowRight,
} from 'lucide-react';

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.25, delay, ease: EASE },
});

function SectionLabel({ children, href, action }: { children: React.ReactNode; href?: string; action?: string }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="text-label">{children}</div>
      {href && (
        <Link
          href={href}
          className="text-[11px] flex items-center gap-1 transition-colors"
          style={{ color: 'var(--text-faint)' }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-secondary)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-faint)'; }}
        >
          {action || 'View all'} <ArrowRight size={10} />
        </Link>
      )}
    </div>
  );
}

function Divider() {
  return <div className="divider" />;
}

function ScoreDot({ score }: { score: number | null }) {
  if (score == null) return null;
  const color = score >= 75 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--text-muted)';
  return (
    <div className="flex items-center gap-1.5">
      <div
        className="w-6 h-6 rounded-md flex items-center justify-center text-[11px] font-bold tabular-nums"
        style={{ background: `${color}18`, color }}
      >
        {score}
      </div>
    </div>
  );
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

  const metrics = [
    { label: 'Jobs Found',   value: a.total_jobs ?? 0,           icon: <Briefcase size={14} style={{ color: 'var(--accent)' }} />,   color: 'var(--accent)',   delay: 0 },
    { label: 'Recruiters',   value: recruiters.length,            icon: <Users size={14} style={{ color: 'var(--green)' }} />,        color: 'var(--green)',    delay: 0.05 },
    { label: 'Applications', value: a.applications_drafted ?? 0, icon: <FileText size={14} style={{ color: 'var(--primary)' }} />,   color: 'var(--primary)',  delay: 0.1 },
    { label: 'Emails Sent',  value: a.emails_sent ?? 0,          icon: <Mail size={14} style={{ color: 'var(--amber)' }} />,         color: 'var(--amber)',    delay: 0.15 },
  ];

  const readiness = [
    { label: 'Resume',   ready: envStatus?.resume_uploaded,           icon: FileText },
    { label: 'Email',    ready: envStatus?.email?.configured,         icon: Mail },
    { label: 'Apollo',   ready: envStatus?.recruiter_discovery?.apollo, icon: Users },
    { label: 'Pipeline', ready: true,                                  icon: CheckCircle2 },
  ];

  return (
    <Shell>
      <div className="space-y-10">
        {/* AI intro — pure typography */}
        <CommandCenter
          analytics={analytics}
          jobs={jobs}
          resumeData={resumeData}
          status={envStatus}
          followupsDue={followupsDue}
          recruiters={recruiters}
        />

        {/* Metric cards */}
        <motion.div {...fadeUp(0.01)} className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {metrics.map(m => (
            <MetricCard key={m.label} label={m.label} value={m.value} icon={m.icon} color={m.color} delay={m.delay} />
          ))}
        </motion.div>

        <Divider />

        {/* System Readiness — horizontal status bar */}
        <motion.div {...fadeUp(0.02)}>
          <SectionLabel>System Readiness</SectionLabel>
          <div className="flex items-center gap-6 flex-wrap">
            {readiness.map(item => (
              <div key={item.label} className="flex items-center gap-2">
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: item.ready ? 'var(--green)' : 'var(--amber)' }}
                />
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                <span
                  className="text-xs font-medium"
                  style={{ color: item.ready ? 'var(--green)' : 'var(--amber)' }}
                >
                  {item.ready ? 'Ready' : 'Needs setup'}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        <Divider />

        {/* Top Matches + Follow-ups */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-16 gap-y-10">
          <motion.div {...fadeUp(0.04)}>
            <SectionLabel href={topJobs.length > 0 ? '/jobs' : undefined}>Top Matches</SectionLabel>
            {topJobs.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No jobs discovered yet.</p>
            ) : (
              <div className="-mx-2">
                {topJobs.map((job, i) => (
                  <Link
                    key={`job-${job.id || i}`}
                    href="/jobs"
                    className="list-row flex items-center gap-3 px-2 py-2.5"
                  >
                    {/* Company avatar */}
                    <div
                      className="w-7 h-7 rounded-md flex items-center justify-center text-[11px] font-bold shrink-0"
                      style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
                    >
                      {(job.company || '?')[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {job.title || '—'}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {job.company || '—'}
                      </div>
                    </div>
                    <ScoreDot score={job.fit_score} />
                  </Link>
                ))}
              </div>
            )}
          </motion.div>

          <motion.div {...fadeUp(0.05)}>
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
                    <span
                      className="badge shrink-0"
                      style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}
                    >
                      Due
                    </span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>

        {/* Matched Companies */}
        {startups.length > 0 && (
          <>
            <Divider />
            <motion.div {...fadeUp(0.06)}>
              <SectionLabel href="/startups">Matched Companies</SectionLabel>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {startups.slice(0, 4).map((s, i) => (
                  <div
                    key={`startup-${i}`}
                    className="p-3 rounded-lg"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div
                        className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold"
                        style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
                      >
                        {(s.company || '?')[0].toUpperCase()}
                      </div>
                      <span
                        className="text-[11px] font-bold tabular-nums"
                        style={{ color: s.overall_score >= 75 ? 'var(--green)' : s.overall_score >= 55 ? 'var(--amber)' : 'var(--text-muted)' }}
                      >
                        {s.overall_score}
                      </span>
                    </div>
                    <div className="text-xs font-medium truncate" style={{ color: 'var(--text)' }}>{s.company}</div>
                    <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                      {s.source}{s.is_remote ? ' · Remote' : ''}
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
