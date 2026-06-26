'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, RefreshCw, Building2, Users, ClipboardCopy, WandSparkles, Target } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { discoverStartups, generateStartupMessage, getStartups, getStartupContacts } from '@/lib/api';

export default function StartupsPage() {
  const [startups, setStartups] = useState<any[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<any>(null);
  const [contacts, setContacts] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadStartups = async () => {
    setLoading(true);
    try {
      const r = await getStartups(20);
      setStartups(r.startups || []);
      if (!selectedCompany && (r.startups || []).length > 0) {
        setSelectedCompany((r.startups || [])[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStartups().catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedCompany?.company) return;
    setBusy(true);
    getStartupContacts(selectedCompany.company, 6)
      .then(r => setContacts(r.contacts || []))
      .catch(() => setContacts([]))
      .finally(() => setBusy(false));
  }, [selectedCompany]);

  const selectedScore = selectedCompany?.overall_score || 0;
  const scoreBadge = selectedScore >= 80 ? 'var(--green)' : selectedScore >= 60 ? 'var(--amber)' : 'var(--red)';

  const handleDiscover = async () => {
    setBusy(true);
    try {
      await discoverStartups(20);
      await loadStartups();
    } finally {
      setBusy(false);
    }
  };

  const handleMessage = async (contact: any) => {
    if (!selectedCompany?.company || !contact?.name) return;
    const r = await generateStartupMessage(selectedCompany.company, contact.name, selectedCompany.summary);
    setMessage(r.message || '');
  };

  const topStats = useMemo(() => {
    return [
      { label: 'Top score', value: startups[0]?.overall_score ?? '—' },
      { label: 'Remote matches', value: startups.filter(s => s.is_remote).length },
      { label: 'Target roles', value: selectedCompany?.matched_roles?.length || 0 },
    ];
  }, [startups, selectedCompany]);

  return (
    <Shell>
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(59,130,246,0.16), rgba(168,85,247,0.12) 45%, rgba(15,15,18,0.98) 100%)',
            borderColor: 'rgba(255,255,255,0.08)',
          }}
        >
          <div className="p-6 md:p-8 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                <Target size={12} />
                Startup Discovery
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight" style={{ color: 'var(--text)' }}>Find remote-first startups that fit your resume.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                Rank Wellfound, Otta, Remote OK, WWR, Ashby, and Y Combinator-style opportunities using resume match, role fit, tech stack, and remote compatibility.
              </p>
            </div>
            <button
              onClick={handleDiscover}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-blue-500/20"
              style={{ background: 'var(--accent)', color: '#fff' }}
            >
              <RefreshCw size={14} className={busy ? 'animate-spin' : ''} />
              Refresh discovery
            </button>
          </div>
        </motion.div>

        <div className="grid grid-cols-3 gap-4">
          {topStats.map(stat => (
            <div key={stat.label} className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
              <div className="text-[10px] uppercase tracking-[0.22em]" style={{ color: 'var(--text-muted)' }}>{stat.label}</div>
              <div className="mt-3 text-2xl font-black" style={{ color: 'var(--text)' }}>{stat.value}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-[1.1fr_0.9fr] gap-5 items-start">
          <div className="rounded-2xl overflow-hidden card-hover" style={{ background: 'var(--surface)' }}>
            <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Top 20 ranked startups</div>
                <div className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Sorted by overall company score.</div>
              </div>
              <Building2 size={16} style={{ color: 'var(--accent)' }} />
            </div>
            <div className="max-h-[620px] overflow-y-auto divide-y" style={{ borderColor: 'var(--border)' }}>
              {loading ? (
                <div className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>Loading...</div>
              ) : startups.length === 0 ? (
                <div className="p-8 text-center" style={{ color: 'var(--text-muted)' }}>No startups yet. Run discovery to build the list.</div>
              ) : startups.map((company, index) => (
                <button
                  key={`${company.company}-${index}`}
                  onClick={() => setSelectedCompany(company)}
                  className="w-full text-left px-5 py-4 transition-colors hover:bg-white/[0.02]"
                  style={{ background: selectedCompany?.company === company.company ? 'rgba(59,130,246,0.08)' : 'transparent' }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{company.company}</div>
                        {company.is_remote && <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'var(--green-muted)', color: 'var(--green)' }}>Remote</span>}
                      </div>
                      <div className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>{company.source} · {company.location || 'Remote'}</div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(company.matched_roles || []).slice(0, 3).map((role: string) => (
                          <span key={role} className="text-[11px] px-2 py-0.5 rounded-md" style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}>{role}</span>
                        ))}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-black" style={{ color: scoreBadge }}>{company.overall_score}</div>
                      <div className="text-[10px] uppercase tracking-[0.22em]" style={{ color: 'var(--text-muted)' }}>overall</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-5">
            <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Selected company</div>
                  <div className="text-lg font-bold mt-1" style={{ color: 'var(--text)' }}>{selectedCompany?.company || 'Select a company'}</div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>{selectedScore}/100</span>
              </div>
              {selectedCompany && (
                <div className="space-y-3 text-sm">
                  {[
                    ['Resume match', selectedCompany.resume_match_score],
                    ['Role match', selectedCompany.role_match_score],
                    ['Tech stack', selectedCompany.tech_stack_match],
                    ['Experience', selectedCompany.experience_match],
                    ['Remote compatibility', selectedCompany.remote_compatibility],
                  ].map(([label, value]) => (
                    <div key={String(label)}>
                      <div className="flex items-center justify-between text-xs mb-1" style={{ color: 'var(--text-muted)' }}><span>{label}</span><span>{value as number}/100</span></div>
                      <div className="h-2 rounded-full" style={{ background: 'var(--border)' }}>
                        <div className="h-2 rounded-full" style={{ width: `${value}%`, background: 'var(--accent)' }} />
                      </div>
                    </div>
                  ))}
                  <div className="pt-2 text-xs leading-6" style={{ color: 'var(--text-secondary)' }}>{selectedCompany.summary}</div>
                </div>
              )}
            </div>

            <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Referral contacts</div>
                  <div className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Apollo-ranked people at the selected company.</div>
                </div>
                <Users size={16} style={{ color: 'var(--purple)' }} />
              </div>
              <div className="space-y-3">
                {busy ? (
                  <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading contacts...</div>
                ) : contacts.length === 0 ? (
                  <div className="text-sm" style={{ color: 'var(--text-muted)' }}>No contacts discovered yet.</div>
                ) : contacts.map((contact, index) => (
                  <div key={`${contact.name}-${index}`} className="rounded-xl p-4 border" style={{ background: 'var(--bg)', borderColor: 'var(--border)' }}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{contact.name}</div>
                        <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{contact.role} · {contact.department || 'General'}</div>
                        <div className="text-[11px] mt-1 font-mono" style={{ color: 'var(--accent)' }}>{contact.email || 'Email unavailable'}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-bold" style={{ color: 'var(--green)' }}>{contact.confidence || 0}%</div>
                        <div className="text-[10px] uppercase tracking-[0.18em]" style={{ color: 'var(--text-muted)' }}>{contact.contact_type || 'contact'}</div>
                      </div>
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => handleMessage(contact)} className="inline-flex items-center gap-2 text-xs px-3 py-2 rounded-lg" style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>
                        <WandSparkles size={12} /> Generate message
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {message && (
              <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>LinkedIn outreach</div>
                    <div className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Short networking note, under 120 words.</div>
                  </div>
                  <ClipboardCopy size={16} style={{ color: 'var(--accent)' }} />
                </div>
                <div className="rounded-xl p-4 text-sm leading-6" style={{ background: 'var(--bg)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                  {message}
                </div>
                <button
                  onClick={() => navigator.clipboard.writeText(message)}
                  className="mt-3 inline-flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
                  style={{ background: 'var(--green-muted)', color: 'var(--green)' }}
                >
                  <ArrowRight size={12} /> Copy to clipboard
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}