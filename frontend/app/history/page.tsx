'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { History, Clock, Briefcase, Send, Mail, CheckCircle2, XCircle, Loader2, Zap } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { getRunHistory } from '@/lib/api';
import { formatDate } from '@/lib/utils';

export default function HistoryPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRunHistory().then(r => setRuns(r.runs || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const statusColor = (status: string) => {
    if (status === 'completed') return 'var(--green)';
    if (status === 'failed' || status === 'error') return 'var(--red)';
    if (status === 'running') return 'var(--primary)';
    return 'var(--text-muted)';
  };

  return (
    <Shell>
      <div className="space-y-5">
        <div>
          <h1 className="text-page-title">History</h1>
          <p className="text-body mt-0.5">{runs.length} pipeline runs</p>
        </div>

        {loading ? (
          <div className="space-y-0">
            {[1,2,3].map(i => <div key={i} className="shimmer h-14 mb-px" />)}
          </div>
        ) : runs.length === 0 ? (
          <EmptyState
            icon={<History size={20} style={{ color: 'var(--text-faint)' }} />}
            title="No runs yet"
            description="Pipeline runs will appear here. Start your first run from Mission Control."
            primaryAction={{ label: 'Go to Mission Control', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div>
            {/* Header */}
            <div className="grid grid-cols-[1fr_100px_80px_80px_80px_100px] gap-3 px-1 py-2 text-[10px] uppercase tracking-wider font-medium"
              style={{ color: 'var(--text-faint)', borderBottom: '1px solid var(--border)' }}>
              <span>Run ID</span>
              <span>Trigger</span>
              <span>Found</span>
              <span>Applied</span>
              <span>Emails</span>
              <span>Status</span>
            </div>

            {runs.map((run, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.01 }}
                className="grid grid-cols-[1fr_100px_80px_80px_80px_100px] gap-3 px-1 py-2.5 items-center transition-colors"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <div className="min-w-0">
                  <span className="text-xs font-mono truncate" style={{ color: 'var(--text)' }}>
                    {run.run_id || '—'}
                  </span>
                  <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                    {formatDate(run.started_at)}
                  </div>
                </div>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{run.triggered_by || '—'}</span>
                <span className="text-xs font-medium tabular-nums" style={{ color: 'var(--text-secondary)' }}>{run.jobs_found ?? '—'}</span>
                <span className="text-xs font-medium tabular-nums" style={{ color: 'var(--text-secondary)' }}>{run.jobs_applied ?? '—'}</span>
                <span className="text-xs font-medium tabular-nums" style={{ color: 'var(--text-secondary)' }}>{run.emails_sent ?? '—'}</span>
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor(run.status) }} />
                  <span className="text-xs capitalize" style={{ color: statusColor(run.status) }}>{run.status || '—'}</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
