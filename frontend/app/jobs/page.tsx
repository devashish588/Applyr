'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, MapPin, Clock, Search, Briefcase } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import JobDetailDrawer from '@/components/jobs/JobDetailDrawer';
import EmptyState from '@/components/ui/EmptyState';
import { getJobs } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const STATUS_FILTERS = ['all', 'found', 'draft', 'ready', 'sent', 'skipped'];

export default function JobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    getJobs().then(r => setJobs(r.jobs || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = jobs.filter(job => {
    const matchesSearch = !search ||
      (job.title || '').toLowerCase().includes(search.toLowerCase()) ||
      (job.company || '').toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || (job.status || 'found') === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusColor = (s: string) => {
    const map: Record<string, string> = {
      sent: 'var(--green)', draft: 'var(--accent)', ready: 'var(--amber)',
      skipped: 'var(--red)', found: 'var(--text-muted)',
    };
    return map[s] || 'var(--text-muted)';
  };

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-page-title">Jobs</h1>
          <p className="text-body mt-0.5">{jobs.length} discovered · {filtered.length} shown</p>
        </div>

        {/* Filters — flat, no cards */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-faint)' }} />
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input"
              style={{ paddingLeft: 30, height: 32 }}
            />
          </div>
          <div className="flex items-center gap-0.5">
            {STATUS_FILTERS.map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className="px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-colors"
                style={{
                  background: statusFilter === s ? 'var(--surface-2)' : 'transparent',
                  color: statusFilter === s ? 'var(--text)' : 'var(--text-muted)',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Jobs — Linear-style table rows, not cards */}
        {loading ? (
          <div className="space-y-0">
            {[1,2,3,4,5].map(i => <div key={i} className="shimmer h-14 mb-px" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Briefcase size={20} style={{ color: 'var(--text-faint)' }} />}
            title={jobs.length === 0 ? 'No jobs discovered yet' : 'No matching jobs'}
            description={jobs.length === 0
              ? 'Run the pipeline to discover and score jobs. Expected: 120+ jobs in ~2 min.'
              : 'Try adjusting your search or filters.'}
            primaryAction={jobs.length === 0 ? { label: 'Run Pipeline', onClick: () => window.location.href = '/pipeline' } : undefined}
          />
        ) : (
          <div>
            {/* Table header */}
            <div className="grid grid-cols-[1fr_160px_80px_60px_100px] gap-3 px-2 py-2 text-[10px] uppercase tracking-wider font-medium"
              style={{ color: 'var(--text-faint)', borderBottom: '1px solid var(--border)' }}>
              <span>Role</span>
              <span>Company</span>
              <span>Source</span>
              <span>Score</span>
              <span>Status</span>
            </div>

            {/* Table rows */}
            {filtered.map((job, i) => {
              const status = job.status || 'found';
              return (
                <motion.div
                  key={job.id || i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.01 }}
                  onClick={() => setSelectedJobId(job.id)}
                  className="grid grid-cols-[1fr_160px_80px_60px_100px] gap-3 px-2 py-2.5 items-center cursor-pointer transition-colors"
                  style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                      {job.title || 'Untitled'}
                    </div>
                    {job.location && (
                      <div className="text-[11px] flex items-center gap-1 mt-0.5" style={{ color: 'var(--text-faint)' }}>
                        <MapPin size={9} /> {job.location}
                      </div>
                    )}
                  </div>
                  <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>
                    {job.company || '—'}
                  </span>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {job.source || '—'}
                  </span>
                  <span className="text-xs font-bold tabular-nums"
                    style={{ color: job.fit_score >= 75 ? 'var(--green)' : job.fit_score >= 50 ? 'var(--amber)' : 'var(--text-muted)' }}>
                    {job.fit_score ?? '—'}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor(status) }} />
                    <span className="text-xs capitalize" style={{ color: statusColor(status) }}>{status}</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      <JobDetailDrawer jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />
    </Shell>
  );
}
