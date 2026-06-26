'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Building2, Send, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { getEmails } from '@/lib/api';

export default function EmailsPage() {
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<'all' | 'drafted' | 'sent'>('all');

  useEffect(() => {
    getEmails().then(r => setEmails(r.emails || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = emails.filter(e => {
    if (filter === 'all') return true;
    if (filter === 'sent') return e.status === 'sent';
    return e.status !== 'sent';
  });

  const copyBody = (email: any, index: number) => {
    navigator.clipboard.writeText(email.email_body || '');
    setCopiedId(index);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Email</h1>
            <p className="text-body mt-0.5">{emails.length} emails — drafted and sent</p>
          </div>
          <div className="flex items-center gap-0.5">
            {(['all', 'drafted', 'sent'] as const).map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-colors"
                style={{
                  background: filter === f ? 'var(--surface-2)' : 'transparent',
                  color: filter === f ? 'var(--text)' : 'var(--text-muted)',
                }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Email list — flat rows, no cards */}
        {loading ? (
          <div className="space-y-0">
            {[1,2,3].map(i => <div key={i} className="shimmer h-12 mb-px" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Mail size={20} style={{ color: 'var(--text-faint)' }} />}
            title="No email drafts yet"
            description="Run the pipeline to generate personalized application emails."
            primaryAction={{ label: 'Run Pipeline', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div>
            {filtered.map((email, i) => {
              const isExpanded = expandedId === i;
              const isSent = email.status === 'sent';
              return (
                <div key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : i)}
                    className="w-full text-left py-3 px-1 flex items-center gap-3 transition-colors"
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: isSent ? 'var(--green)' : 'var(--primary)' }} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {email.email_subject || 'No subject'}
                      </div>
                      <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {email.hr_email || 'No recipient'}
                        {email.company && <> · {email.company}</>}
                      </div>
                    </div>
                    <span className="text-xs shrink-0" style={{ color: isSent ? 'var(--green)' : 'var(--text-muted)' }}>
                      {isSent ? 'Sent' : 'Draft'}
                    </span>
                    {isExpanded ? <ChevronUp size={13} style={{ color: 'var(--text-faint)' }} /> : <ChevronDown size={13} style={{ color: 'var(--text-faint)' }} />}
                  </button>

                  {isExpanded && email.email_body && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      className="px-6 pb-3"
                    >
                      <pre
                        className="text-xs leading-relaxed whitespace-pre-wrap max-h-[200px] overflow-y-auto py-3 px-3 rounded-md"
                        style={{ background: 'var(--surface)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}
                      >
                        {email.email_body}
                      </pre>
                      <button onClick={() => copyBody(email, i)} className="btn btn-ghost btn-sm mt-2">
                        {copiedId === i ? <><Check size={11} /> Copied</> : <><Copy size={11} /> Copy</>}
                      </button>
                    </motion.div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Shell>
  );
}
