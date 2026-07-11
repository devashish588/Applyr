'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Building2, WandSparkles, Check, ClipboardCopy, X } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import ProgressBar from '@/components/ui/ProgressBar';
import { discoverStartups, generateStartupMessage, getStartups, getStartupContacts } from '@/lib/api';

function ScoreDimension({ label, value }: { label: string; value: number }) {
  const color = value >= 75 ? 'var(--green)' : value >= 55 ? 'var(--accent)' : value >= 35 ? 'var(--amber)' : 'var(--text-muted)';
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
        <span className="tabular-nums font-medium" style={{ color }}>{value}</span>
      </div>
      <ProgressBar value={value} height={3} color={color} />
    </div>
  );
}

export default function StartupsPage() {
  const [startups, setStartups] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [contacts, setContacts] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);

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
    setContacts([]);
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
    setGeneratingFor(contact.name);
    try {
      const r = await generateStartupMessage(selectedCompany.company, contact.name, selectedCompany.summary);
      setMessage(r.message || '');
    } finally { setGeneratingFor(null); }
  };

  const copyMessage = () => {
    navigator.clipboard.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Shell>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Companies</h1>
            <p className="text-body mt-0.5">{startups.length} companies ranked by fit</p>
          </div>
          <button id="discover-btn" onClick={handleDiscover} disabled={busy} className="btn btn-secondary btn-sm">
            <RefreshCw size={12} className={busy ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="space-y-0">{[1,2,3,4].map(i => <div key={i} className="shimmer h-12 mb-px" />)}</div>
        ) : startups.length === 0 ? (
          <EmptyState
            icon={<Building2 size={22} style={{ color: 'var(--text-faint)' }} />}
            title="No companies discovered yet"
            description="Run discovery to rank remote-first startups against your resume profile. Expected: 20+ companies."
            primaryAction={{ label: 'Run Discovery', onClick: handleDiscover }}
          />
        ) : (
          <div className="grid gap-8" style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'start' }}>
            {/* Company list */}
            <div>
              <div
                className="grid gap-3 px-1 py-2 text-[10px] uppercase tracking-wider font-semibold"
                style={{
                  gridTemplateColumns: '1fr 56px',
                  color: 'var(--text-faint)',
                  borderBottom: '1px solid var(--border)',
                }}
              >
                <span>Company</span>
                <span className="text-right">Score</span>
              </div>
              <div className="max-h-[600px] overflow-y-auto">
                {startups.map((company, index) => {
                  const isSelected = selectedCompany?.company === company.company;
                  const scoreColor = company.overall_score >= 75 ? 'var(--green)' : company.overall_score >= 55 ? 'var(--amber)' : 'var(--text-muted)';
                  return (
                    <button
                      key={`${company.company}-${index}`}
                      id={`company-row-${index}`}
                      onClick={() => { setSelectedCompany(company); setMessage(''); }}
                      className="w-full text-left grid gap-3 px-1 py-2.5 items-center transition-all"
                      style={{
                        gridTemplateColumns: '1fr 56px',
                        background: isSelected ? 'var(--primary-subtle)' : 'transparent',
                        borderBottom: '1px solid var(--border-subtle)',
                        borderLeft: isSelected ? '2px solid var(--primary)' : '2px solid transparent',
                        paddingLeft: isSelected ? 'calc(0.25rem - 2px)' : '0.25rem',
                      }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--surface-hover)'; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold shrink-0"
                            style={{ background: isSelected ? 'var(--primary-muted)' : 'var(--surface-2)', color: isSelected ? 'var(--primary)' : 'var(--text-muted)' }}
                          >
                            {(company.company || '?')[0].toUpperCase()}
                          </div>
                          <span className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                            {company.company}
                          </span>
                          {company.is_remote && (
                            <span className="text-[9px] font-medium" style={{ color: 'var(--green)' }}>Remote</span>
                          )}
                        </div>
                        <div className="text-[11px] mt-0.5 ml-7" style={{ color: 'var(--text-faint)' }}>
                          {company.source}{company.location ? ` · ${company.location}` : ''}
                        </div>
                      </div>
                      <span
                        className="text-sm font-bold tabular-nums text-right"
                        style={{ color: scoreColor }}
                      >
                        {company.overall_score}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Detail panel */}
            <AnimatePresence mode="wait">
              {selectedCompany && (
                <motion.div
                  key={selectedCompany.company}
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-5 sticky top-16"
                >
                  {/* Company heading */}
                  <div className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-base font-bold shrink-0"
                      style={{ background: 'var(--primary-muted)', color: 'var(--primary)' }}
                    >
                      {(selectedCompany.company || '?')[0].toUpperCase()}
                    </div>
                    <div>
                      <div className="text-base font-bold" style={{ color: 'var(--text)' }}>
                        {selectedCompany.company}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        Score {selectedCompany.overall_score}/100
                        {selectedCompany.is_remote && <span style={{ color: 'var(--green)' }}> · Remote</span>}
                      </div>
                    </div>
                  </div>

                  {/* Score dimensions */}
                  <div className="space-y-2.5">
                    {[
                      ['Resume Match', selectedCompany.resume_match_score],
                      ['Role Match',   selectedCompany.role_match_score],
                      ['Tech Stack',   selectedCompany.tech_stack_match],
                      ['Experience',   selectedCompany.experience_match],
                      ['Remote Compat',selectedCompany.remote_compatibility],
                    ].map(([label, value]) => (
                      <ScoreDimension key={String(label)} label={String(label)} value={Number(value)} />
                    ))}
                  </div>

                  {selectedCompany.summary && (
                    <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {selectedCompany.summary}
                    </p>
                  )}

                  <div className="divider" />

                  {/* Contacts */}
                  <div>
                    <div className="text-label mb-3">Contacts</div>
                    {busy ? (
                      <div className="space-y-2">{[1,2].map(i => <div key={i} className="shimmer h-10 rounded-lg" />)}</div>
                    ) : contacts.length === 0 ? (
                      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No contacts found.</p>
                    ) : (
                      <div className="space-y-0">
                        {contacts.map((contact, idx) => (
                          <div
                            key={`${contact.name}-${idx}`}
                            className="py-2.5"
                            style={{ borderBottom: '1px solid var(--border-subtle)' }}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                                  {contact.name}
                                </span>
                                <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
                                  {contact.role}
                                </span>
                              </div>
                              <span className="text-xs tabular-nums" style={{ color: 'var(--text-faint)' }}>
                                {contact.confidence}%
                              </span>
                            </div>
                            {contact.email && (
                              <div className="text-[11px] font-mono mt-0.5" style={{ color: 'var(--accent)' }}>
                                {contact.email}
                              </div>
                            )}
                            <button
                              onClick={() => handleMessage(contact)}
                              disabled={generatingFor === contact.name}
                              className="btn btn-ghost btn-sm mt-1.5"
                              style={{ height: 24, padding: '2px 8px', fontSize: 11 }}
                            >
                              <WandSparkles size={10} />
                              {generatingFor === contact.name ? 'Generating…' : 'Message'}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Generated message */}
                  {message && (
                    <div>
                      <div className="text-label mb-2">Outreach Message</div>
                      <pre
                        className="text-xs leading-relaxed whitespace-pre-wrap py-3 px-4 rounded-xl"
                        style={{
                          background: 'var(--surface)',
                          color: 'var(--text-secondary)',
                          border: '1px solid var(--border)',
                          maxHeight: 200,
                          overflow: 'auto',
                        }}
                      >
                        {message}
                      </pre>
                      <button onClick={copyMessage} className="btn btn-ghost btn-sm mt-2">
                        {copied ? <><Check size={11} /> Copied</> : <><ClipboardCopy size={11} /> Copy</>}
                      </button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </Shell>
  );
}