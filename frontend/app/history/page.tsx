'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { History, CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { getRunHistory } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const STATUS_CONFIG: Record<string, { badge: string; icon: any; color: string }> = {
  completed: { badge: 'badge-green',   icon: CheckCircle2, color: 'var(--green)' },
  failed:    { badge: 'badge-red',     icon: XCircle,      color: 'var(--red)' },
  error:     { badge: 'badge-red',     icon: XCircle,      color: 'var(--red)' },
  running:   { badge: 'badge-primary', icon: Loader2,      color: 'var(--primary)' },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || { badge: 'badge-neutral', icon: Clock, color: 'var(--text-muted)' };
  const Icon = cfg.icon;
  return (
    <span className={`badge ${cfg.badge}`}>
      <Icon size={9} className={status === 'running' ? 'animate-spin' : ''} />
      {status}
    </span>
  );
}

function Stat({ value, label }: { value: any; label: string }) {
  return (
    <div className="text-center">
      <div className="text-sm font-bold tabular-nums" style={{ color: 'var(--text)' }}>
        {value ?? '—'}
      </div>
      <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>{label}</div>
    </div>
  );
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRunHistory().then(r => setRuns(r.runs || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <Shell>
      <div className="space-y-5">
        <div>
          <h1 className="text-page-title">History</h1>
          <p className="text-body mt-0.5">{runs.length} pipeline runs</p>
        </div>

        {loading ? (
          <div className="space-y-0">
            {[1,2,3].map(i => <div key={i} className="shimmer skeleton-row" style={{ height: 56, marginBottom: 1 }} />)}
          </div>
        ) : runs.length === 0 ? (
          <EmptyState
            icon={<History size={22} style={{ color: 'var(--text-faint)' }} />}
            title="No runs yet"
            description="Pipeline runs will appear here. Start your first run from Mission Control."
            primaryAction={{ label: 'Go to Mission Control', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div>
            {/* Table header */}
            <div
              className="grid gap-4 px-3 py-2 text-[10px] uppercase tracking-wider font-semibold"
              style={{
                gridTemplateColumns: '1fr 120px 80px 80px 80px 120px',
                color: 'var(--text-faint)',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <span>Run ID</span>
              <span>Trigger</span>
              <span className="text-center">Found</span>
              <span className="text-center">Applied</span>
              <span className="text-center">Emails</span>
              <span>Status</span>
            </div>

            {runs.map((run, i) => (
              <motion.div
                key={i}
                id={`run-row-${i}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: Math.min(i * 0.015, 0.2) }}
                className="grid gap-4 px-3 py-3 items-center transition-all"
                style={{
                  gridTemplateColumns: '1fr 120px 80px 80px 80px 120px',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                {/* Run ID + date */}
                <div className="min-w-0">
                  <div
                    className="text-xs font-mono truncate"
                    style={{ color: 'var(--text)' }}
                  >
                    {run.run_id || '—'}
                  </div>
                  <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                    {formatDate(run.started_at)}
                  </div>
                </div>

                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {run.triggered_by || '—'}
                </span>

                <Stat value={run.jobs_found} label="found" />
                <Stat value={run.jobs_applied} label="applied" />
                <Stat value={run.emails_sent} label="emails" />

                <StatusBadge status={run.status || 'unknown'} />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
