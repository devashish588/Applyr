'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  CalendarClock, Briefcase, Building2, RefreshCw, Plus,
  GripVertical, ExternalLink, Clock,
} from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { createApplication, getApplications, getFollowupsDue } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const COLUMNS = [
  { id: 'saved', label: 'Saved', color: 'var(--text-muted)' },
  { id: 'ready_to_apply', label: 'Ready', color: 'var(--accent)' },
  { id: 'applied', label: 'Applied', color: 'var(--primary)' },
  { id: 'follow_up_due', label: 'Follow-up', color: 'var(--amber)' },
  { id: 'interview', label: 'Interview', color: 'var(--green)' },
  { id: 'offer', label: 'Offer', color: '#34D399' },
  { id: 'rejected', label: 'Rejected', color: 'var(--red)' },
];

export default function TrackerPage() {
  const [applications, setApplications] = useState<any[]>([]);
  const [followups, setFollowups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [apps, due] = await Promise.all([getApplications(), getFollowupsDue()]);
      setApplications(apps.applications || []);
      setFollowups(due.applications || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load().catch(() => {}); }, [load]);

  const grouped = useMemo(() => {
    const map: Record<string, any[]> = {};
    COLUMNS.forEach(c => { map[c.id] = []; });
    applications.forEach(app => {
      const status = (app.application_status || 'saved').toLowerCase();
      const key = Object.keys(map).includes(status) ? status : 'saved';
      map[key].push(app);
    });
    return map;
  }, [applications]);

  const totalApps = applications.length;

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
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Application Tracker</h1>
            <p className="text-body mt-1">
              {totalApps} applications across {COLUMNS.length} stages
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => load()} className="btn btn-secondary btn-sm">
              <RefreshCw size={13} /> Refresh
            </button>
            <button onClick={addDemoEntry} disabled={saving} className="btn btn-primary btn-sm">
              <Plus size={13} /> Add entry
            </button>
          </div>
        </div>

        {/* Follow-ups — flat, no card */}
        {followups.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <CalendarClock size={13} style={{ color: 'var(--amber)' }} />
              <span className="text-label" style={{ color: 'var(--amber)' }}>
                {followups.length} follow-up{followups.length !== 1 ? 's' : ''} due
              </span>
            </div>
            <div className="space-y-0">
              {followups.slice(0, 4).map((item, i) => (
                <div key={i} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <div className="min-w-0">
                    <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                      {item.company} · {item.role}
                    </span>
                    <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
                      {formatDate(item.follow_up_date)}
                    </span>
                  </div>
                  <span className="badge badge-amber shrink-0">Due</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Kanban Board */}
        {loading ? (
          <div className="grid grid-cols-7 gap-3">
            {COLUMNS.map(col => (
              <div key={col.id} className="space-y-2">
                <div className="shimmer h-8 rounded-lg" />
                <div className="shimmer h-24 rounded-lg" />
                <div className="shimmer h-24 rounded-lg" />
              </div>
            ))}
          </div>
        ) : totalApps === 0 ? (
          <EmptyState
            icon={<Briefcase size={24} style={{ color: 'var(--text-faint)' }} />}
            title="No applications tracked yet"
            description="Applications from the pipeline will appear here automatically. You can also add entries manually."
            primaryAction={{ label: 'Add sample entry', onClick: addDemoEntry }}
            secondaryAction={{ label: 'Go to Pipeline', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div className="grid grid-cols-7 gap-3 items-start" style={{ minHeight: 400 }}>
            {COLUMNS.map(col => {
              const cards = grouped[col.id] || [];
              return (
                <div key={col.id} className="space-y-2">
                  {/* Column header */}
                  <div className="flex items-center justify-between px-2 py-1.5">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: col.color }}
                      />
                      <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                        {col.label}
                      </span>
                    </div>
                    <span
                      className="text-[10px] font-medium px-1.5 py-0.5 rounded-full tabular-nums"
                      style={{ background: 'var(--surface-2)', color: 'var(--text-faint)' }}
                    >
                      {cards.length}
                    </span>
                  </div>

                  {/* Cards */}
                  <div className="space-y-2 min-h-[60px]">
                    {cards.map((app, i) => (
                      <motion.div
                        key={`${app.company}-${app.role}-${i}`}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className="card p-3 group"
                        style={{ cursor: 'default' }}
                      >
                        <div className="text-sm font-medium leading-tight" style={{ color: 'var(--text)' }}>
                          {app.role || '—'}
                        </div>
                        <div className="text-[11px] mt-1 flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                          <Building2 size={10} />
                          {app.company || '—'}
                        </div>
                        {app.source && (
                          <div className="mt-2">
                            <span className="badge badge-neutral" style={{ fontSize: 9 }}>
                              {app.source}
                            </span>
                          </div>
                        )}
                        {app.follow_up_date && (
                          <div className="mt-2 flex items-center gap-1 text-[10px]" style={{ color: 'var(--amber)' }}>
                            <Clock size={9} />
                            {formatDate(app.follow_up_date)}
                          </div>
                        )}
                        {app.job_url && (
                          <a
                            href={app.job_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-2 text-[10px] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            style={{ color: 'var(--primary)' }}
                          >
                            <ExternalLink size={9} /> Open listing
                          </a>
                        )}
                      </motion.div>
                    ))}

                    {cards.length === 0 && (
                      <div
                        className="rounded-xl border-2 border-dashed p-4 text-center"
                        style={{ borderColor: 'var(--border)', color: 'var(--text-faint)' }}
                      >
                        <span className="text-[11px]">No items</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Shell>
  );
}