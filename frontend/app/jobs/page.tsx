'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, MapPin, Search, Briefcase, X } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import JobDetailDrawer from '@/components/jobs/JobDetailDrawer';
import EmptyState from '@/components/ui/EmptyState';
import { getJobs } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const STATUS_FILTERS = ['all', 'found', 'draft', 'ready', 'sent', 'skipped'];

const STATUS_BADGE: Record<string, string> = {
  sent:    'badge-green',
  draft:   'badge-blue',
  ready:   'badge-amber',
  skipped: 'badge-red',
  found:   'badge-neutral',
};

function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span style={{ color: 'var(--text-faint)' }}>—</span>;
  const color = score >= 75 ? 'var(--green)' : score >= 50 ? 'var(--amber)' : 'var(--text-muted)';
  const bg    = score >= 75 ? 'var(--green-subtle)' : score >= 50 ? 'var(--amber-subtle)' : 'var(--surface-2)';
  return (
    <div
      className="inline-flex items-center justify-center w-9 h-6 rounded-md text-xs font-bold tabular-nums"
      style={{ background: bg, color }}
    >
      {score}
    </div>
  );
}

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

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-page-title">Jobs</h1>
          <p className="text-body mt-0.5">
            {jobs.length} discovered
            {filtered.length !== jobs.length && ` · ${filtered.length} shown`}
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <div className="relative" style={{ width: 260 }}>
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-faint)' }} />
            <input
              type="text"
              id="jobs-search"
              placeholder="Search by role or company..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input"
              style={{ paddingLeft: 30, paddingRight: search ? 30 : 10, height: 32 }}
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 transition-colors"
                style={{ color: 'var(--text-faint)' }}
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-muted)'; }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-faint)'; }}
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Status pills */}
          <div
            className="flex items-center gap-0.5 p-0.5 rounded-lg"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            {STATUS_FILTERS.map(s => (
              <button
                key={s}
                id={`filter-${s}`}
                onClick={() => setStatusFilter(s)}
                className="px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-all"
                style={{
                  background: statusFilter === s ? 'var(--surface-2)' : 'transparent',
                  color: statusFilter === s ? 'var(--text)' : 'var(--text-muted)',
                  boxShadow: statusFilter === s ? 'var(--shadow-sm)' : 'none',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="space-y-0">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="shimmer skeleton-row rounded-none" style={{ borderRadius: 0, height: 52, marginBottom: 1 }} />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Briefcase size={22} style={{ color: 'var(--text-faint)' }} />}
            title={jobs.length === 0 ? 'No jobs discovered yet' : 'No matching jobs'}
            description={
              jobs.length === 0
                ? 'Run the pipeline to discover and score jobs. Expected: 120+ jobs in ~2 min.'
                : 'Try adjusting your search or filters.'
            }
            primaryAction={jobs.length === 0 ? { label: 'Run Pipeline', onClick: () => window.location.href = '/pipeline' } : undefined}
          />
        ) : (
          <div>
            {/* Table header */}
            <div
              className="grid gap-3 px-3 py-2 text-[10px] uppercase tracking-wider font-semibold"
              style={{
                gridTemplateColumns: '1fr 150px 80px 60px 100px',
                color: 'var(--text-faint)',
                borderBottom: '1px solid var(--border)',
              }}
            >
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
                  transition={{ delay: Math.min(i * 0.008, 0.2) }}
                  onClick={() => setSelectedJobId(job.id)}
                  id={`job-row-${job.id || i}`}
                  className="grid gap-3 px-3 py-3 items-center cursor-pointer transition-all"
                  style={{
                    gridTemplateColumns: '1fr 150px 80px 60px 100px',
                    borderBottom: '1px solid var(--border-subtle)',
                    borderLeft: '2px solid transparent',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'var(--surface-hover)';
                    e.currentTarget.style.borderLeftColor = 'var(--primary)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.borderLeftColor = 'transparent';
                  }}
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
                  <ScoreBadge score={job.fit_score} />
                  <span className={`badge ${STATUS_BADGE[status] || 'badge-neutral'}`}>
                    {status}
                  </span>
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
