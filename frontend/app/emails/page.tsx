'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, ChevronDown, ChevronUp, Copy, Check, Send, Inbox } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { getEmails } from '@/lib/api';

type EmailFilter = 'all' | 'drafted' | 'sent';

export default function EmailsPage() {
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [filter, setFilter] = useState<EmailFilter>('all');

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

  const sentCount    = emails.filter(e => e.status === 'sent').length;
  const draftedCount = emails.filter(e => e.status !== 'sent').length;

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Email</h1>
            <p className="text-body mt-0.5">
              {draftedCount} draft{draftedCount !== 1 ? 's' : ''} · {sentCount} sent
            </p>
          </div>

          {/* Filter tabs */}
          <div
            className="flex items-center gap-0.5 p-0.5 rounded-lg"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            {(['all', 'drafted', 'sent'] as EmailFilter[]).map(f => (
              <button
                key={f}
                id={`email-filter-${f}`}
                onClick={() => setFilter(f)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-all"
                style={{
                  background: filter === f ? 'var(--surface-2)' : 'transparent',
                  color: filter === f ? 'var(--text)' : 'var(--text-muted)',
                }}
              >
                {f === 'sent' && <Send size={9} />}
                {f === 'drafted' && <Inbox size={9} />}
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Email list */}
        {loading ? (
          <div className="space-y-0">
            {[1,2,3].map(i => <div key={i} className="shimmer h-14 mb-px" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Mail size={22} style={{ color: 'var(--text-faint)' }} />}
            title="No email drafts yet"
            description="Run the pipeline to generate personalized application emails."
            primaryAction={{ label: 'Run Pipeline', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div>
            {filtered.map((email, i) => {
              const isExpanded = expandedId === i;
              const isSent = email.status === 'sent';
              const statusColor = isSent ? 'var(--green)' : 'var(--primary)';

              return (
                <div key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <button
                    id={`email-row-${i}`}
                    onClick={() => setExpandedId(isExpanded ? null : i)}
                    className="w-full text-left py-3 px-2 flex items-center gap-3 transition-all rounded-sm"
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    {/* Status dot */}
                    <div
                      className="w-6 h-6 rounded-md flex items-center justify-center shrink-0"
                      style={{ background: isSent ? 'var(--green-muted)' : 'var(--primary-muted)' }}
                    >
                      {isSent
                        ? <Send size={11} style={{ color: 'var(--green)' }} />
                        : <Mail size={11} style={{ color: 'var(--primary)' }} />
                      }
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                        {email.email_subject || 'No subject'}
                      </div>
                      <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {email.hr_email || 'No recipient'}
                        {email.company && <> · {email.company}</>}
                      </div>
                    </div>

                    <span
                      className="badge shrink-0"
                      style={{
                        background: isSent ? 'var(--green-muted)' : 'var(--primary-muted)',
                        color: statusColor,
                      }}
                    >
                      {isSent ? 'Sent' : 'Draft'}
                    </span>

                    <span style={{ color: 'var(--text-faint)' }}>
                      {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </span>
                  </button>

                  {/* Expanded email body */}
                  <AnimatePresence>
                    {isExpanded && email.email_body && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="px-4 pb-4">
                          {/* Email preview header */}
                          <div
                            className="rounded-xl overflow-hidden"
                            style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
                          >
                            <div
                              className="px-4 py-2.5 space-y-0.5"
                              style={{ borderBottom: '1px solid var(--border)' }}
                            >
                              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>To:</span>{' '}
                                {email.hr_email || 'Not discovered'}
                              </div>
                              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Subject:</span>{' '}
                                {email.email_subject || '—'}
                              </div>
                            </div>
                            <div className="px-4 py-3">
                              <pre
                                className="text-xs leading-relaxed whitespace-pre-wrap max-h-[200px] overflow-y-auto"
                                style={{ color: 'var(--text-secondary)', fontFamily: 'inherit' }}
                              >
                                {email.email_body}
                              </pre>
                            </div>
                          </div>
                          <button
                            id={`copy-email-${i}`}
                            onClick={() => copyBody(email, i)}
                            className="btn btn-ghost btn-sm mt-2"
                          >
                            {copiedId === i ? <><Check size={11} /> Copied</> : <><Copy size={11} /> Copy body</>}
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Shell>
  );
}
