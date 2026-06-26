'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, AlertTriangle, Shield, Copy, Check, ExternalLink } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { getRecruiters } from '@/lib/api';

export default function RecruitersPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  useEffect(() => {
    getRecruiters().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const recruiters = data?.recruiters || [];
  const warnings = data?.warnings || [];
  const apiStatus = data?.api_status || {};

  const copyEmail = (email: string) => {
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div>
          <h1 className="text-page-title">Recruiters</h1>
          <p className="text-body mt-0.5">{recruiters.length} contacts discovered</p>
        </div>

        {/* API Status — flat inline */}
        <div className="flex items-center gap-6">
          {Object.entries(apiStatus).map(([key, ok]) => (
            <div key={key} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: ok ? 'var(--green)' : 'var(--red)' }} />
              <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{key}</span>
              <span className="text-xs" style={{ color: ok ? 'var(--green)' : 'var(--red)' }}>
                {ok ? 'Connected' : 'Missing'}
              </span>
            </div>
          ))}
        </div>

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="space-y-1">
            {warnings.map((w: string, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs" style={{ color: 'var(--amber)' }}>
                <AlertTriangle size={11} /> {w}
              </div>
            ))}
          </div>
        )}

        {/* Recruiter list — table, no cards */}
        {loading ? (
          <div className="space-y-0">
            {[1,2,3,4].map(i => <div key={i} className="shimmer h-12 mb-px" />)}
          </div>
        ) : recruiters.length === 0 ? (
          <EmptyState
            icon={<Users size={20} style={{ color: 'var(--text-faint)' }} />}
            title="No recruiters discovered yet"
            description="Run the pipeline with Apollo enabled to find HR contacts. Expected: 25+ recruiters per run."
            primaryAction={{ label: 'Run Pipeline', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div>
            {/* Table header */}
            <div className="grid grid-cols-[1fr_1fr_1fr_80px_60px_40px] gap-3 px-1 py-2 text-[10px] uppercase tracking-wider font-medium"
              style={{ color: 'var(--text-faint)', borderBottom: '1px solid var(--border)' }}>
              <span>Name</span>
              <span>Role</span>
              <span>Email</span>
              <span>Source</span>
              <span>Conf.</span>
              <span></span>
            </div>

            {recruiters.map((r: any, i: number) => (
              <motion.div
                key={`${r.name}-${i}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.01 }}
                className="grid grid-cols-[1fr_1fr_1fr_80px_60px_40px] gap-3 px-1 py-2.5 items-center transition-colors"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-6 h-6 rounded flex items-center justify-center shrink-0 text-[10px] font-bold"
                    style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
                  >
                    {(r.name || '?')[0].toUpperCase()}
                  </div>
                  <span className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                    {r.name || '—'}
                  </span>
                </div>
                <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>
                  {r.role || '—'}
                </span>
                <div className="flex items-center gap-1.5 min-w-0">
                  {r.email ? (
                    <>
                      <span className="text-xs font-mono truncate" style={{ color: 'var(--accent)' }}>{r.email}</span>
                      <button
                        onClick={() => copyEmail(r.email)}
                        className="shrink-0 p-0.5 rounded transition-colors"
                        style={{ color: 'var(--text-faint)' }}
                      >
                        {copiedEmail === r.email ? <Check size={10} style={{ color: 'var(--green)' }} /> : <Copy size={10} />}
                      </button>
                    </>
                  ) : (
                    <span className="text-xs" style={{ color: 'var(--text-faint)' }}>—</span>
                  )}
                </div>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.source || '—'}</span>
                <span className="text-xs font-bold tabular-nums"
                  style={{ color: (r.confidence || 0) >= 70 ? 'var(--green)' : 'var(--text-muted)' }}>
                  {r.confidence || 0}%
                </span>
                <div>
                  {r.linkedin && (
                    <a href={r.linkedin} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-faint)' }}>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
