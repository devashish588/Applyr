'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Building2, Send } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { getEmails } from '@/lib/api';
import { getScoreColor } from '@/lib/utils';

export default function EmailsPage() {
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEmails().then(r => setEmails(r.emails || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <Shell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>Email Drafts</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Ready-to-send application emails — drafted vs sent
          </p>
        </div>

        <div className="rounded-xl overflow-hidden card-hover" style={{ background: 'var(--surface)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['To', 'Subject', 'Company', 'Score', 'Status'].map(h => (
                  <th key={h} className="text-left text-[11px] uppercase tracking-wider font-semibold px-4 py-3"
                      style={{ color: 'var(--text-muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>Loading...</td></tr>
              ) : emails.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>No email drafts yet</td></tr>
              ) : (
                emails.map((e, i) => (
                  <motion.tr
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    className="hover:bg-white/[0.02]"
                    style={{ borderBottom: '1px solid rgba(39,39,42,0.5)' }}
                  >
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {e.hr_email || '—'}
                    </td>
                    <td className="px-4 py-3" style={{ color: 'var(--text)' }}>
                      {e.email_subject || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                        <Building2 size={12} />
                        {e.company || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {e.fit_score != null ? (
                        <div className="flex items-center gap-2">
                          <div className="w-12 h-1.5 rounded-full" style={{ background: 'var(--border)' }}>
                            <div className="h-full rounded-full" style={{
                              width: `${e.fit_score}%`,
                              background: getScoreColor(e.fit_score),
                            }} />
                          </div>
                          <span className="text-[11px] font-mono" style={{ color: getScoreColor(e.fit_score) }}>
                            {e.fit_score}
                          </span>
                        </div>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] font-medium px-2 py-0.5 rounded flex items-center gap-1 w-fit"
                            style={{
                              background: e.status === 'sent' ? 'var(--green-muted)' : 'var(--accent-muted)',
                              color: e.status === 'sent' ? 'var(--green)' : 'var(--accent)',
                            }}>
                        {e.status === 'sent' ? <Send size={10} /> : <Mail size={10} />}
                        {e.status === 'sent' ? 'Sent' : 'Drafted'}
                      </span>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
