'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { History, Clock } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { getRunHistory } from '@/lib/api';
import { formatDate } from '@/lib/utils';

export default function HistoryPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRunHistory().then(r => setRuns(r.runs || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const statusStyle = (status: string) => {
    if (status === 'completed') return { bg: 'var(--green-muted)', color: 'var(--green)' };
    if (status === 'failed' || status === 'error') return { bg: 'var(--red-muted)', color: 'var(--red)' };
    if (status === 'running') return { bg: 'var(--accent-muted)', color: 'var(--accent)' };
    return { bg: 'var(--surface-2)', color: 'var(--text-muted)' };
  };

  return (
    <Shell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>Run History</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Every pipeline run logged here
          </p>
        </div>

        <div className="rounded-xl overflow-hidden card-hover" style={{ background: 'var(--surface)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Run ID', 'Trigger', 'Started', 'Found', 'Applied', 'Emails', 'Status'].map(h => (
                  <th key={h} className="text-left text-[11px] uppercase tracking-wider font-semibold px-4 py-3"
                      style={{ color: 'var(--text-muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>Loading...</td></tr>
              ) : runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
                    <History size={24} className="mx-auto mb-2 opacity-40" />
                    No runs yet
                  </td>
                </tr>
              ) : (
                runs.map((run, i) => {
                  const ss = statusStyle(run.status);
                  return (
                    <motion.tr
                      key={i}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="hover:bg-white/[0.02]"
                      style={{ borderBottom: '1px solid rgba(39,39,42,0.5)' }}
                    >
                      <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {run.run_id || '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] px-2 py-0.5 rounded"
                              style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>
                          {run.triggered_by || '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                        {formatDate(run.started_at)}
                      </td>
                      <td className="px-4 py-3 font-medium" style={{ color: 'var(--text)' }}>
                        {run.jobs_found ?? '—'}
                      </td>
                      <td className="px-4 py-3" style={{ color: 'var(--text)' }}>
                        {run.jobs_applied ?? '—'}
                      </td>
                      <td className="px-4 py-3" style={{ color: 'var(--text)' }}>
                        {run.emails_sent ?? '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                              style={{ background: ss.bg, color: ss.color }}>
                          {run.status || '—'}
                        </span>
                      </td>
                    </motion.tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
