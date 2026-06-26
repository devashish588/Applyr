'use client';

import { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import ProgressBar from '@/components/ui/ProgressBar';
import { getAnalytics, getJobs, getApplications, getRecruiters } from '@/lib/api';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [recruiters, setRecruiters] = useState<any[]>([]);

  useEffect(() => {
    getAnalytics().then(r => setAnalytics(r.analytics)).catch(() => {});
    getJobs().then(r => setJobs(r.jobs || [])).catch(() => {});
    getApplications().then(r => setApplications(r.applications || [])).catch(() => {});
    getRecruiters().then(r => setRecruiters(r.recruiters || [])).catch(() => {});
  }, []);

  const a = analytics || {};

  const funnel = useMemo(() => {
    const found = a.total_jobs || 0;
    const drafted = a.applications_drafted || 0;
    const submitted = a.applications_submitted || 0;
    const emails = a.emails_sent || 0;
    return [
      { label: 'Discovered', value: found, pct: 100 },
      { label: 'Drafted', value: drafted, pct: found ? Math.round((drafted / found) * 100) : 0 },
      { label: 'Submitted', value: submitted, pct: found ? Math.round((submitted / found) * 100) : 0 },
      { label: 'Emails Sent', value: emails, pct: found ? Math.round((emails / found) * 100) : 0 },
    ];
  }, [a]);

  const sourceBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    jobs.forEach(j => { counts[j.source || 'unknown'] = (counts[j.source || 'unknown'] || 0) + 1; });
    return Object.entries(counts).sort(([, a], [, b]) => b - a).slice(0, 6);
  }, [jobs]);

  const scoreDistribution = useMemo(() => {
    const buckets = { '80+': 0, '60–79': 0, '40–59': 0, '<40': 0 };
    jobs.forEach(j => {
      const s = j.fit_score;
      if (s == null) return;
      if (s >= 80) buckets['80+']++;
      else if (s >= 60) buckets['60–79']++;
      else if (s >= 40) buckets['40–59']++;
      else buckets['<40']++;
    });
    return Object.entries(buckets);
  }, [jobs]);

  const avgScore = useMemo(() => {
    const scored = jobs.filter(j => j.fit_score != null);
    if (scored.length === 0) return 0;
    return Math.round(scored.reduce((sum, j) => sum + j.fit_score, 0) / scored.length);
  }, [jobs]);

  const appStatusBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    applications.forEach(app => { counts[(app.application_status || 'saved').toLowerCase()] = (counts[(app.application_status || 'saved').toLowerCase()] || 0) + 1; });
    return Object.entries(counts).sort(([, a], [, b]) => b - a);
  }, [applications]);

  return (
    <Shell>
      <div className="space-y-10">
        {/* Header */}
        <div>
          <h1 className="text-page-title">Analytics</h1>
          <p className="text-body mt-0.5">Performance insights across your pipeline.</p>
        </div>

        {/* Top stats — flat, no cards */}
        <div className="grid grid-cols-5 gap-8">
          {[
            { label: 'Jobs Found', value: a.total_jobs ?? 0 },
            { label: 'Drafted', value: a.applications_drafted ?? 0 },
            { label: 'Submitted', value: a.applications_submitted ?? 0 },
            { label: 'Emails Sent', value: a.emails_sent ?? 0 },
            { label: 'Recruiters', value: recruiters.length },
          ].map(m => (
            <div key={m.label}>
              <div className="text-2xl font-bold tabular-nums" style={{ color: 'var(--text)' }}>{m.value}</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{m.label}</div>
            </div>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Funnel + Score side by side — no cards */}
        <div className="grid grid-cols-2 gap-12">
          <div>
            <div className="text-label mb-4">Application Funnel</div>
            <div className="space-y-3">
              {funnel.map(stage => (
                <div key={stage.label}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span style={{ color: 'var(--text-secondary)' }}>{stage.label}</span>
                    <span className="tabular-nums" style={{ color: 'var(--text-muted)' }}>{stage.value} ({stage.pct}%)</span>
                  </div>
                  <ProgressBar value={stage.pct} height={4} />
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-label mb-4">Score Distribution</div>
            <div className="mb-4">
              <span className="text-3xl font-bold tabular-nums" style={{ color: 'var(--text)' }}>{avgScore}</span>
              <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>avg fit score</span>
            </div>
            <div className="space-y-3">
              {scoreDistribution.map(([label, count]) => {
                const total = jobs.filter(j => j.fit_score != null).length || 1;
                const color = label === '80+' ? 'var(--green)' : label === '60–79' ? 'var(--accent)' : label === '40–59' ? 'var(--amber)' : 'var(--red)';
                return (
                  <div key={label}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                      <span className="font-medium tabular-nums" style={{ color }}>{count}</span>
                    </div>
                    <ProgressBar value={count} max={total} color={color} height={4} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Source + App Status — no cards */}
        <div className="grid grid-cols-2 gap-12">
          <div>
            <div className="text-label mb-4">Jobs by Source</div>
            {sourceBreakdown.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No data yet</p>
            ) : (
              <div className="space-y-2.5">
                {sourceBreakdown.map(([source, count]) => (
                  <div key={source} className="flex items-center justify-between">
                    <span className="text-sm capitalize" style={{ color: 'var(--text-secondary)' }}>{source}</span>
                    <span className="text-sm font-bold tabular-nums" style={{ color: 'var(--text)' }}>{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="text-label mb-4">Application Status</div>
            {appStatusBreakdown.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No applications tracked</p>
            ) : (
              <div className="space-y-2.5">
                {appStatusBreakdown.map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className="text-sm capitalize" style={{ color: 'var(--text-secondary)' }}>{status.replace(/_/g, ' ')}</span>
                    <span className="text-sm font-bold tabular-nums" style={{ color: 'var(--text)' }}>{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
