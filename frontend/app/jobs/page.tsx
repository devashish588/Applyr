'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, MapPin, ExternalLink } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import JobDetailDrawer from '@/components/jobs/JobDetailDrawer';
import { getJobs } from '@/lib/api';
import { getScoreColor, formatDate } from '@/lib/utils';

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getJobs().then(r => setJobs(r.jobs || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const statusStyle = (status: string) => {
    const map: Record<string, { bg: string; color: string }> = {
      sent: { bg: 'var(--green-muted)', color: 'var(--green)' },
      draft: { bg: 'var(--accent-muted)', color: 'var(--accent)' },
      ready: { bg: 'var(--amber-muted)', color: 'var(--amber)' },
      skipped: { bg: 'var(--red-muted)', color: 'var(--red)' },
      found: { bg: 'var(--surface-2)', color: 'var(--text-muted)' },
    };
    return map[status] || map.found;
  };

  return (
    <Shell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>Jobs</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            All discovered and processed job listings — click any row for details
          </p>
        </div>

        <div className="rounded-xl overflow-hidden card-hover" style={{ background: 'var(--surface)' }}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Role', 'Company', 'Location', 'Fit Score', 'Source', 'Status', 'Date'].map(h => (
                    <th key={h} className="text-left text-[11px] uppercase tracking-wider font-semibold px-4 py-3"
                        style={{ color: 'var(--text-muted)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
                      Loading...
                    </td>
                  </tr>
                ) : jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
                      No jobs found yet — run the pipeline
                    </td>
                  </tr>
                ) : (
                  jobs.map((job, i) => {
                    const ss = statusStyle(job.status);
                    return (
                      <motion.tr
                        key={job.id || i}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: i * 0.02 }}
                        className="cursor-pointer transition-colors hover:bg-white/[0.02]"
                        style={{ borderBottom: '1px solid rgba(39,39,42,0.5)' }}
                        onClick={() => setSelectedJobId(job.id)}
                      >
                        <td className="px-4 py-3 font-medium" style={{ color: 'var(--text)' }}>
                          {job.title || '—'}
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                            <Building2 size={12} />
                            {job.company || 'Unknown Company'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                            <MapPin size={11} />
                            {job.location || '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {job.fit_score != null ? (
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 rounded-full" style={{ background: 'var(--border)' }}>
                                <div className="h-full rounded-full transition-all" style={{
                                  width: `${job.fit_score}%`,
                                  background: getScoreColor(job.fit_score),
                                }} />
                              </div>
                              <span className="text-[11px] font-mono tabular-nums"
                                    style={{ color: getScoreColor(job.fit_score) }}>
                                {job.fit_score}
                              </span>
                            </div>
                          ) : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[11px] px-2 py-0.5 rounded"
                                style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}>
                            {job.source || '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                                style={{ background: ss.bg, color: ss.color }}>
                            {job.status || 'found'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                          {formatDate(job.scraped_at)}
                        </td>
                      </motion.tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <JobDetailDrawer jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />
    </Shell>
  );
}
