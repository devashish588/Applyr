'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, AlertTriangle, Shield, Copy, Check, ExternalLink, Mail } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { getRecruiters } from '@/lib/api';

function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  const initials = (name || '?').split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
  const hue = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div
      className="flex items-center justify-center rounded-full shrink-0 text-white font-bold"
      style={{
        width: size,
        height: size,
        background: `linear-gradient(135deg, hsl(${hue},65%,55%), hsl(${(hue + 60) % 360},65%,50%))`,
        fontSize: size * 0.35,
      }}
    >
      {initials}
    </div>
  );
}

function ConfidenceBadge({ value }: { value: number }) {
  const color = value >= 70 ? 'var(--green)' : value >= 50 ? 'var(--amber)' : 'var(--text-muted)';
  const bg    = value >= 70 ? 'var(--green-muted)' : value >= 50 ? 'var(--amber-muted)' : 'var(--surface-2)';
  return (
    <span
      className="badge"
      style={{ background: bg, color }}
    >
      {value}%
    </span>
  );
}

export default function RecruitersPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

  useEffect(() => {
    getRecruiters().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const recruiters  = data?.recruiters || [];
  const warnings    = data?.warnings || [];
  const apiStatus   = data?.api_status || {};

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

        {/* API Status */}
        <div className="flex items-center gap-5">
          {Object.entries(apiStatus).map(([key, ok]) => (
            <div key={key} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: ok ? 'var(--green)' : 'var(--red)' }} />
              <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{key}</span>
              <span className="text-xs font-medium" style={{ color: ok ? 'var(--green)' : 'var(--red)' }}>
                {ok ? 'Connected' : 'Missing'}
              </span>
            </div>
          ))}
        </div>

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="space-y-1">
            {warnings.map((w: string, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
                style={{ background: 'var(--amber-subtle)', color: 'var(--amber)' }}>
                <AlertTriangle size={11} /> {w}
              </div>
            ))}
          </div>
        )}

        {/* Recruiter table */}
        {loading ? (
          <div className="space-y-0">
            {[1,2,3,4].map(i => (
              <div key={i} className="shimmer skeleton-row" style={{ height: 56, marginBottom: 1 }} />
            ))}
          </div>
        ) : recruiters.length === 0 ? (
          <EmptyState
            icon={<Users size={22} style={{ color: 'var(--text-faint)' }} />}
            title="No recruiters discovered yet"
            description="Run the pipeline with Apollo enabled to find HR contacts. Expected: 25+ recruiters per run."
            primaryAction={{ label: 'Run Pipeline', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div>
            {/* Table header */}
            <div
              className="grid gap-3 px-2 py-2 text-[10px] uppercase tracking-wider font-semibold"
              style={{
                gridTemplateColumns: '200px 1fr 1fr 80px 60px 40px',
                color: 'var(--text-faint)',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <span>Name</span>
              <span>Role</span>
              <span>Email</span>
              <span>Source</span>
              <span>Conf.</span>
              <span />
            </div>

            {recruiters.map((r: any, i: number) => (
              <motion.div
                key={`${r.name}-${i}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: Math.min(i * 0.01, 0.15) }}
                className="grid gap-3 px-2 py-3 items-center transition-all"
                id={`recruiter-row-${i}`}
                style={{
                  gridTemplateColumns: '200px 1fr 1fr 80px 60px 40px',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                {/* Name + avatar */}
                <div className="flex items-center gap-2.5 min-w-0">
                  <Avatar name={r.name || '?'} size={28} />
                  <span className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                    {r.name || '—'}
                  </span>
                </div>

                <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>
                  {r.role || '—'}
                </span>

                {/* Email with copy */}
                <div className="flex items-center gap-1.5 min-w-0">
                  {r.email ? (
                    <>
                      <Mail size={10} style={{ color: 'var(--text-faint)', flexShrink: 0 }} />
                      <span className="text-xs font-mono truncate" style={{ color: 'var(--accent)' }}>{r.email}</span>
                      <button
                        onClick={() => copyEmail(r.email)}
                        className="shrink-0 p-0.5 rounded transition-colors"
                        style={{ color: 'var(--text-faint)' }}
                        title="Copy email"
                        onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-secondary)'; }}
                        onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-faint)'; }}
                      >
                        {copiedEmail === r.email ? <Check size={10} style={{ color: 'var(--green)' }} /> : <Copy size={10} />}
                      </button>
                    </>
                  ) : (
                    <span className="text-xs" style={{ color: 'var(--text-faint)' }}>—</span>
                  )}
                </div>

                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.source || '—'}</span>
                <ConfidenceBadge value={r.confidence || 0} />

                {/* LinkedIn */}
                <div>
                  {r.linkedin && (
                    <a
                      href={r.linkedin}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="transition-colors"
                      style={{ color: 'var(--text-faint)' }}
                      onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent)'; }}
                      onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-faint)'; }}
                    >
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
