'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, Building2, Users, ClipboardCopy, WandSparkles, Check } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import ProgressBar from '@/components/ui/ProgressBar';
import { discoverStartups, generateStartupMessage, getStartups, getStartupContacts } from '@/lib/api';

export default function StartupsPage() {
  const [startups, setStartups] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [contacts, setContacts] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadStartups = async () => {
    setLoading(true);
    try {
      const r = await getStartups(20);
      setStartups(r.startups || []);
      if (!selectedCompany && (r.startups || []).length > 0) setSelectedCompany((r.startups || [])[0]);
    } finally { setLoading(false); }
  };

  useEffect(() => { loadStartups().catch(() => {}); }, []);

  useEffect(() => {
    if (!selectedCompany?.company) return;
    setBusy(true);
    getStartupContacts(selectedCompany.company, 6)
      .then(r => setContacts(r.contacts || []))
      .catch(() => setContacts([]))
      .finally(() => setBusy(false));
  }, [selectedCompany]);

  const handleDiscover = async () => {
    setBusy(true);
    try { await discoverStartups(20); await loadStartups(); } finally { setBusy(false); }
  };

  const handleMessage = async (contact: any) => {
    if (!selectedCompany?.company || !contact?.name) return;
    const r = await generateStartupMessage(selectedCompany.company, contact.name, selectedCompany.summary);
    setMessage(r.message || '');
  };

  const copyMessage = () => { navigator.clipboard.writeText(message); setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Companies</h1>
            <p className="text-body mt-0.5">{startups.length} companies ranked by fit</p>
          </div>
          <button onClick={handleDiscover} disabled={busy} className="btn btn-secondary btn-sm">
            <RefreshCw size={12} className={busy ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="space-y-0">{[1,2,3,4].map(i => <div key={i} className="shimmer h-10 mb-px" />)}</div>
        ) : startups.length === 0 ? (
          <EmptyState
            icon={<Building2 size={20} style={{ color: 'var(--text-faint)' }} />}
            title="No companies discovered yet"
            description="Run discovery to rank remote-first startups against your resume profile. Expected: 20+ companies."
            primaryAction={{ label: 'Run Discovery', onClick: handleDiscover }}
          />
        ) : (
          <div className="grid grid-cols-[1fr_1fr] gap-8 items-start">
            {/* Company list — flat table */}
            <div>
              <div className="grid grid-cols-[1fr_70px] gap-3 px-1 py-2 text-[10px] uppercase tracking-wider font-medium"
                style={{ color: 'var(--text-faint)', borderBottom: '1px solid var(--border)' }}>
                <span>Company</span>
                <span className="text-right">Score</span>
              </div>
              <div className="max-h-[600px] overflow-y-auto">
                {startups.map((company, index) => {
                  const isSelected = selectedCompany?.company === company.company;
                  return (
                    <button
                      key={`${company.company}-${index}`}
                      onClick={() => setSelectedCompany(company)}
                      className="w-full text-left grid grid-cols-[1fr_70px] gap-3 px-1 py-2.5 items-center transition-colors"
                      style={{
                        background: isSelected ? 'var(--primary-muted)' : 'transparent',
                        borderBottom: '1px solid var(--border-subtle)',
                      }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--surface-hover)'; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = isSelected ? 'var(--primary-muted)' : 'transparent'; }}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>{company.company}</span>
                          {company.is_remote && <span className="text-[9px]" style={{ color: 'var(--green)' }}>Remote</span>}
                        </div>
                        <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                          {company.source}{company.location ? ` · ${company.location}` : ''}
                        </div>
                      </div>
                      <span className="text-sm font-bold tabular-nums text-right"
                        style={{ color: company.overall_score >= 75 ? 'var(--green)' : company.overall_score >= 55 ? 'var(--amber)' : 'var(--text-muted)' }}>
                        {company.overall_score}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Detail panel — flat sections */}
            <div className="space-y-6 sticky top-16">
              {selectedCompany && (
                <>
                  <div>
                    <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>{selectedCompany.company}</div>
                    <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      Score {selectedCompany.overall_score}/100
                    </div>
                  </div>

                  <div className="space-y-2.5">
                    {[
                      ['Resume Match', selectedCompany.resume_match_score],
                      ['Role Match', selectedCompany.role_match_score],
                      ['Tech Stack', selectedCompany.tech_stack_match],
                      ['Experience', selectedCompany.experience_match],
                      ['Remote', selectedCompany.remote_compatibility],
                    ].map(([label, value]) => (
                      <div key={String(label)}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span style={{ color: 'var(--text-muted)' }}>{label as string}</span>
                          <span className="tabular-nums" style={{ color: 'var(--text-faint)' }}>{value as number}</span>
                        </div>
                        <ProgressBar value={value as number} height={3} />
                      </div>
                    ))}
                  </div>

                  {selectedCompany.summary && (
                    <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {selectedCompany.summary}
                    </p>
                  )}

                  <div style={{ borderTop: '1px solid var(--border)' }} />

                  {/* Contacts */}
                  <div>
                    <div className="text-label mb-3">Contacts</div>
                    {busy ? (
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Loading...</p>
                    ) : contacts.length === 0 ? (
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No contacts found.</p>
                    ) : (
                      <div className="space-y-0">
                        {contacts.map((contact, idx) => (
                          <div key={`${contact.name}-${idx}`} className="py-2.5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>{contact.name}</span>
                                <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>{contact.role}</span>
                              </div>
                              <span className="text-xs tabular-nums" style={{ color: 'var(--text-faint)' }}>{contact.confidence}%</span>
                            </div>
                            {contact.email && (
                              <div className="text-[11px] font-mono mt-0.5" style={{ color: 'var(--accent)' }}>{contact.email}</div>
                            )}
                            <button onClick={() => handleMessage(contact)} className="btn btn-ghost btn-sm mt-1.5" style={{ padding: '2px 6px', height: 22 }}>
                              <WandSparkles size={10} /> Message
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Generated message */}
                  {message && (
                    <div>
                      <div className="text-label mb-2">Outreach</div>
                      <pre className="text-xs leading-relaxed whitespace-pre-wrap py-3 px-3 rounded-md"
                        style={{ background: 'var(--surface)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
                        {message}
                      </pre>
                      <button onClick={copyMessage} className="btn btn-ghost btn-sm mt-2">
                        {copied ? <><Check size={11} /> Copied</> : <><ClipboardCopy size={11} /> Copy</>}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}