'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { CalendarClock, Briefcase, Building2, Mail, RefreshCw, MessageSquareText, CheckCircle2 } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { createApplication, getApplications, getFollowupsDue } from '@/lib/api';
import { formatDate } from '@/lib/utils';

export default function TrackerPage() {
  const [applications, setApplications] = useState<any[]>([]);
  const [followups, setFollowups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [apps, due] = await Promise.all([getApplications(), getFollowupsDue()]);
      setApplications(apps.applications || []);
      setFollowups(due.applications || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const metrics = useMemo(() => {
    const status = applications.reduce((acc, item) => {
      const key = (item.application_status || 'saved').toLowerCase();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    return [
      { label: 'Saved', value: status.saved || 0 },
      { label: 'Ready to Apply', value: status.ready_to_apply || 0 },
      { label: 'Applied', value: status.applied || 0 },
      { label: 'Follow-ups Due', value: followups.length },
    ];
  }, [applications, followups]);

  const addDemoEntry = async () => {
    setSaving(true);
    try {
      await createApplication({
        company: 'Demo Startup',
        role: 'Backend Engineer',
        job_url: `https://demo.example/jobs/${Date.now()}`,
        source: 'startups',
        application_status: 'saved',
        email_status: 'pending',
      });
      await load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Shell>
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(59,130,246,0.14), rgba(34,197,94,0.10) 40%, rgba(15,15,18,0.98) 100%)',
            borderColor: 'rgba(255,255,255,0.08)',
          }}
        >
          <div className="p-6 md:p-8 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                <CheckCircle2 size={12} />
                Application Tracker
              </div>
              <h1 className="mt-4 text-3xl font-black tracking-tight" style={{ color: 'var(--text)' }}>Track every application, follow-up, and referral.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                Keep career-page applications, outreach, ATS scores, and reminders in one place.
              </p>
            </div>
            <div className="flex gap-3">
              <button onClick={load} className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold" style={{ background: 'var(--surface-2)', color: 'var(--text)' }}>
                <RefreshCw size={14} /> Refresh
              </button>
              <button onClick={addDemoEntry} className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold" style={{ background: 'var(--accent)', color: '#fff' }}>
                <Briefcase size={14} /> Add sample row
              </button>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-4 gap-4">
          {metrics.map(stat => (
            <div key={stat.label} className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
              <div className="text-[10px] uppercase tracking-[0.22em]" style={{ color: 'var(--text-muted)' }}>{stat.label}</div>
              <div className="mt-3 text-2xl font-black" style={{ color: 'var(--text)' }}>{stat.value}</div>
            </div>
          ))}
        </div>

        {followups.length > 0 && (
          <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center gap-2 mb-4">
              <CalendarClock size={14} style={{ color: 'var(--amber)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Follow-ups due</span>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              {followups.map((item, i) => (
                <div key={i} className="rounded-xl p-4 border" style={{ background: 'var(--bg)', borderColor: 'var(--border)' }}>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{item.company} · {item.role}</div>
                      <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>Due {formatDate(item.follow_up_date)}</div>
                      <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{item.referral_contact || 'No referral contact yet'}</div>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}>Follow-up due</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-2xl overflow-hidden card-hover" style={{ background: 'var(--surface)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Company', 'Role', 'Job URL', 'Source', 'Status', 'Email', 'Follow-up'].map(h => (
                  <th key={h} className="text-left text-[11px] uppercase tracking-wider font-semibold px-4 py-3" style={{ color: 'var(--text-muted)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>Loading...</td></tr>
              ) : applications.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>No applications tracked yet</td></tr>
              ) : applications.map((app, i) => (
                <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }} className="hover:bg-white/[0.02]" style={{ borderBottom: '1px solid rgba(39,39,42,0.5)' }}>
                  <td className="px-4 py-3 font-medium" style={{ color: 'var(--text)' }}>{app.company || '—'}</td>
                  <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>{app.role || '—'}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: 'var(--accent)' }}>
                    {app.job_url ? <a href={app.job_url} target="_blank" rel="noreferrer">Open</a> : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] px-2 py-0.5 rounded-full" style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}>{app.source || '—'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] px-2 py-0.5 rounded-full" style={{ background: app.application_status === 'applied' ? 'var(--green-muted)' : app.application_status === 'follow_up_due' ? 'var(--amber-muted)' : 'var(--accent-muted)', color: app.application_status === 'applied' ? 'var(--green)' : app.application_status === 'follow_up_due' ? 'var(--amber)' : 'var(--accent)' }}>
                      {app.application_status || 'saved'}
                    </span>
                  </td>
                  <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>{app.email_status || 'pending'}</td>
                  <td className="px-4 py-3" style={{ color: 'var(--text-muted)' }}>{app.follow_up_date ? formatDate(app.follow_up_date) : '—'}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-2xl p-5 card-hover" style={{ background: 'var(--surface)' }}>
          <div className="flex items-center gap-2 mb-3">
            <MessageSquareText size={14} style={{ color: 'var(--purple)' }} />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Tracking rules</span>
          </div>
          <ul className="space-y-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <li>• First follow-up is scheduled 5-7 days after application.</li>
            <li>• A second follow-up can be set 10-14 days after that.</li>
            <li>• Reminders stop when the status becomes Interview, Offer, or Rejected.</li>
            <li>• Referral contact, resume version, ATS scores, and note history are stored with each row.</li>
          </ul>
        </div>
      </div>
    </Shell>
  );
}