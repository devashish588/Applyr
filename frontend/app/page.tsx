'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Briefcase, FileText, Mail, Send, TrendingUp, Activity, Zap, AlertTriangle,
} from 'lucide-react';
import Shell from '@/components/layout/Shell';
import ResumeUploadCard from '@/components/resume/ResumeUploadCard';
import ResumePreviewCard from '@/components/resume/ResumePreviewCard';
import ProfileGenerationCard from '@/components/resume/ProfileGenerationCard';
import ResumeHealthCard from '@/components/resume/ResumeHealthCard';
import SearchStrategyCard from '@/components/search/SearchStrategyCard';
import { getAnalytics, getJobs, getStatus, getSearchStrategy, getResumeParsed, getFollowupsDue, getStartups } from '@/lib/api';
import { getScoreColor, formatDate } from '@/lib/utils';
import { ArrowUpRight, Sparkles, ShieldCheck, Gauge } from 'lucide-react';

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [envStatus, setEnvStatus] = useState<any>(null);
  const [resumeData, setResumeData] = useState<any>(null);
  const [strategy, setStrategy] = useState<any>(null);
  const [followupsDue, setFollowupsDue] = useState<any[]>([]);
  const [startups, setStartups] = useState<any[]>([]);

  const loadData = useCallback(() => {
    getAnalytics().then(r => setAnalytics(r.analytics)).catch(() => {});
    getJobs().then(r => setJobs((r.jobs || []).slice(0, 6))).catch(() => {});
    getStatus().then(setEnvStatus).catch(() => {});
    getSearchStrategy().then(r => setStrategy(r.strategy)).catch(() => {});
    getFollowupsDue().then(r => setFollowupsDue(r.applications || [])).catch(() => {});
    getStartups(6).then(r => setStartups(r.startups || [])).catch(() => {});
    getResumeParsed().then(r => {
      if (r.success) setResumeData(r);
    }).catch(() => {});
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const a = analytics || {};

  const analyticsTiles = [
    {
      label: 'Coverage',
      value: a.total_jobs ?? '—',
      hint: 'jobs tracked',
      color: 'var(--accent)',
      icon: ArrowUpRight,
    },
    {
      label: 'Drafted',
      value: a.applications_drafted ?? '—',
      hint: 'ready to review',
      color: 'var(--purple)',
      icon: Sparkles,
    },
    {
      label: 'Submitted',
      value: a.applications_submitted ?? '0',
      hint: 'live actions',
      color: 'var(--green)',
      icon: ShieldCheck,
    },
    {
      label: 'Emails',
      value: a.emails_sent ?? '0',
      hint: 'provider ready',
      color: 'var(--amber)',
      icon: Mail,
    },
    {
      label: 'Startup matches',
      value: a.startup_matches ?? startups.length ?? '—',
      hint: 'ranked targets',
      color: 'var(--purple)',
      icon: Sparkles,
    },
    {
      label: 'Follow-ups due',
      value: a.followups_due ?? followupsDue.length ?? '—',
      hint: 'needs attention',
      color: 'var(--amber)',
      icon: Mail,
    },
  ];

  const stats = [
    { icon: Briefcase, label: 'Jobs Found', value: a.total_jobs ?? '—', color: 'var(--accent)' },
    { icon: FileText, label: 'Drafted', value: a.applications_drafted ?? '—', color: 'var(--purple)' },
    { icon: Send, label: 'Submitted', value: a.applications_submitted ?? '0', color: 'var(--green)' },
    { icon: Mail, label: 'Emails Sent', value: a.emails_sent ?? '0', color: 'var(--amber)' },
  ];

  const handleUploadComplete = () => {
    setTimeout(loadData, 500);
  };

  return (
    <Shell>
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(168,85,247,0.10) 44%, rgba(15,15,18,0.98) 100%)',
            borderColor: 'rgba(255,255,255,0.08)',
          }}
        >
          <div className="p-6 md:p-8 flex items-start justify-between gap-6 flex-col md:flex-row">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                <Gauge size={12} />
                Live analytics
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight" style={{ color: 'var(--text)' }}>Your pipeline, visualized like an operations board.</h1>
              <p className="mt-3 text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                Track discovery, drafts, submissions, and email readiness from a single glance.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 min-w-[280px] w-full md:w-auto">
              {[
                { label: 'Dry run', value: a.dry_run ? 'On' : 'Off', color: a.dry_run ? 'var(--amber)' : 'var(--green)' },
                { label: 'Run mode', value: a.dry_run ? 'Drafting only' : 'Submitting', color: 'var(--text)' },
              ].map((item) => (
                <div key={item.label} className="rounded-2xl border p-4" style={{ background: 'rgba(15,15,18,0.6)', borderColor: 'rgba(255,255,255,0.08)' }}>
                  <div className="text-[10px] uppercase tracking-[0.22em]" style={{ color: 'var(--text-muted)' }}>{item.label}</div>
                  <div className="mt-3 text-lg font-bold" style={{ color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-4 gap-4">
          {analyticsTiles.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-2xl p-5 card-hover"
              style={{ background: 'var(--surface)' }}
            >
              <div className="flex items-center gap-2 mb-4">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                     style={{ background: `color-mix(in srgb, ${stat.color} 14%, transparent)` }}>
                  <stat.icon size={16} style={{ color: stat.color }} />
                </div>
              </div>
              <div className="text-3xl font-black tracking-tight" style={{ color: 'var(--text)' }}>
                {stat.value}
              </div>
              <div className="text-xs mt-1 uppercase tracking-[0.18em]" style={{ color: 'var(--text-muted)' }}>
                {stat.label}
              </div>
              <div className="text-xs mt-3" style={{ color: 'var(--text-secondary)' }}>
                {stat.hint}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Dry Run warning in stats */}
        {a.dry_run && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs"
            style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}
          >
            <AlertTriangle size={13} />
            <span>
              Metrics show <strong>drafted</strong> counts. No applications have been submitted (DRY RUN mode).
            </span>
          </motion.div>
        )}

        {/* Resume Trust Layer */}
        <div className="grid grid-cols-2 gap-5">
          <ResumeUploadCard onUploadComplete={handleUploadComplete} />
          <ResumePreviewCard data={resumeData?.parsed_json || null} />
        </div>

        <div className="grid grid-cols-2 gap-5">
          <ProfileGenerationCard roles={resumeData?.roles_json || []} />
          <ResumeHealthCard health={resumeData?.health_json || null} />
        </div>

        {/* Search Strategy */}
        {strategy && <SearchStrategyCard strategy={strategy} />}

        {startups.length > 0 && (
          <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Startup Matches</div>
                <div className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Best remote-first companies from discovery.</div>
              </div>
              <Sparkles size={16} style={{ color: 'var(--purple)' }} />
            </div>
            <div className="grid md:grid-cols-3 gap-3">
              {startups.slice(0, 3).map((startup, i) => (
                <div key={i} className="rounded-xl p-4 border" style={{ background: 'var(--bg)', borderColor: 'var(--border)' }}>
                  <div className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{startup.company}</div>
                  <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{startup.overall_score}/100 overall score</div>
                  <div className="mt-3 flex items-center justify-between text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    <span>{startup.source}</span>
                    <span>{startup.is_remote ? 'Remote' : 'Hybrid'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {followupsDue.length > 0 && (
          <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center gap-2 mb-4">
              <Mail size={14} style={{ color: 'var(--amber)' }} />
              <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Follow-ups due</div>
            </div>
            <div className="space-y-2">
              {followupsDue.slice(0, 3).map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: 'var(--bg)', border: '1px solid var(--border)' }}>
                  <div>
                    <div className="text-sm font-medium" style={{ color: 'var(--text)' }}>{item.company} · {item.role}</div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{formatDate(item.follow_up_date)}</div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}>Due</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Jobs + System Status */}
        <div className="grid grid-cols-2 gap-5">
          {/* Recent Jobs */}
          <div className="rounded-xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-4"
                 style={{ color: 'var(--text-muted)' }}>
              Recent Jobs
            </div>
            {jobs.length === 0 ? (
              <div className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>
                No jobs yet — run the pipeline
              </div>
            ) : (
              <div className="space-y-1">
                {jobs.map((job, i) => (
                  <div key={i} className="flex items-center justify-between py-2 px-2 rounded-md hover:bg-white/[0.02] transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {job.title || '—'}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {job.company || '—'}
                      </div>
                    </div>
                    {job.fit_score != null && (
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                          <div className="h-full rounded-full" style={{
                            width: `${job.fit_score}%`,
                            background: getScoreColor(job.fit_score),
                          }} />
                        </div>
                        <span className="text-[11px] font-mono tabular-nums w-7 text-right"
                              style={{ color: getScoreColor(job.fit_score) }}>
                          {job.fit_score}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* System Status */}
          <div className="rounded-xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-4"
                 style={{ color: 'var(--text-muted)' }}>
              System Status
            </div>
            {envStatus ? (
              <div className="space-y-2">
                {Object.entries(envStatus.env_keys || {}).map(([key, ok]) => (
                  <div key={key} className="flex items-center justify-between py-1.5 border-b"
                       style={{ borderColor: 'var(--border)' }}>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{key}</span>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                          style={{
                            background: ok ? 'var(--green-muted)' : 'var(--red-muted)',
                            color: ok ? 'var(--green)' : 'var(--red)',
                          }}>
                      {ok ? '✓ Set' : '✗ Missing'}
                    </span>
                  </div>
                ))}
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>Resume</span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                        style={{
                          background: envStatus.resume_uploaded ? 'var(--green-muted)' : 'var(--amber-muted)',
                          color: envStatus.resume_uploaded ? 'var(--green)' : 'var(--amber)',
                        }}>
                    {envStatus.resume_uploaded ? '✓ Uploaded' : '⚠ Missing'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading...</div>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
