'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  CalendarClock, Briefcase, Building2, RefreshCw, Plus,
  ExternalLink, Clock,
} from 'lucide-react';
import Shell from '@/components/layout/Shell';
import EmptyState from '@/components/ui/EmptyState';
import { createApplication, getApplications, getFollowupsDue } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const COLUMNS = [
  { id: 'saved',         label: 'Saved',     color: 'var(--stage-saved)',     headerBg: 'rgba(139,139,149,0.12)' },
  { id: 'ready_to_apply',label: 'Ready',     color: 'var(--stage-ready)',     headerBg: 'var(--accent-muted)' },
  { id: 'applied',       label: 'Applied',   color: 'var(--stage-applied)',   headerBg: 'var(--primary-muted)' },
  { id: 'follow_up_due', label: 'Follow-up', color: 'var(--stage-followup)',  headerBg: 'var(--amber-muted)' },
  { id: 'interview',     label: 'Interview', color: 'var(--stage-interview)', headerBg: 'var(--cyan-muted)' },
  { id: 'offer',         label: 'Offer',     color: 'var(--stage-offer)',     headerBg: 'var(--green-muted)' },
  { id: 'rejected',      label: 'Rejected',  color: 'var(--stage-rejected)',  headerBg: 'var(--red-muted)' },
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
            <button id="tracker-refresh-btn" onClick={() => load()} className="btn btn-secondary btn-sm">
              <RefreshCw size={12} /> Refresh
            </button>
            <button id="tracker-add-btn" onClick={addDemoEntry} disabled={saving} className="btn btn-primary btn-sm">
              <Plus size={12} /> Add entry
            </button>
          </div>
        </div>

        {/* Follow-ups banner */}
        {followups.length > 0 && (
          <div
            className="flex items-center gap-3 px-4 py-3 rounded-xl"
            style={{ background: 'var(--amber-muted)', border: '1px solid rgba(251,191,36,0.2)' }}
          >
            <CalendarClock size={14} style={{ color: 'var(--amber)', flexShrink: 0 }} />
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium" style={{ color: 'var(--amber)' }}>
                {followups.length} follow-up{followups.length !== 1 ? 's' : ''} due
              </span>
              <span className="text-xs ml-2" style={{ color: 'var(--amber)', opacity: 0.75 }}>
                {followups.slice(0, 2).map(f => `${f.company} · ${f.role}`).join(', ')}
                {followups.length > 2 ? ` +${followups.length - 2} more` : ''}
              </span>
            </div>
          </div>
        )}

        {/* Kanban Board */}
        {loading ? (
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${COLUMNS.length}, 1fr)` }}>
            {COLUMNS.map(col => (
              <div key={col.id} className="space-y-2">
                <div className="shimmer h-9 rounded-lg" />
                <div className="shimmer h-24 rounded-lg" />
                <div className="shimmer h-20 rounded-lg" />
              </div>
            ))}
          </div>
        ) : totalApps === 0 ? (
          <EmptyState
            icon={<Briefcase size={22} style={{ color: 'var(--text-faint)' }} />}
            title="No applications tracked yet"
            description="Applications from the pipeline will appear here automatically. You can also add entries manually."
            primaryAction={{ label: 'Add sample entry', onClick: addDemoEntry }}
            secondaryAction={{ label: 'Go to Pipeline', onClick: () => window.location.href = '/pipeline' }}
          />
        ) : (
          <div
            className="grid gap-3 items-start"
            style={{ gridTemplateColumns: `repeat(${COLUMNS.length}, minmax(0, 1fr))`, minHeight: 400 }}
          >
            {COLUMNS.map(col => {
              const cards = grouped[col.id] || [];
              return (
                <div key={col.id} className="kanban-column">
                  {/* Column header with gradient top strip */}
                  <div
                    className="kanban-col-header"
                    style={{ '--col-color': col.color } as any}
                  >
                    <div
                      className="absolute top-0 left-0 right-0 h-0.5"
                      style={{ background: col.color }}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold" style={{ color: col.color }}>
                        {col.label}
                      </span>
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded-full tabular-nums"
                        style={{ background: col.headerBg, color: col.color }}
                      >
                        {cards.length}
                      </span>
                    </div>
                  </div>

                  {/* Cards */}
                  <div className="p-2 space-y-2 min-h-[60px]">
                    {cards.map((app, i) => (
                      <motion.div
                        key={`${app.company}-${app.role}-${i}`}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.04 }}
                        className="kanban-card group"
                      >
                        {/* Company avatar + role */}
                        <div className="flex items-start gap-2 mb-1.5">
                          <div
                            className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5"
                            style={{ background: 'var(--surface-3)', color: 'var(--text-muted)' }}
                          >
                            {(app.company || '?')[0].toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <div className="text-xs font-semibold leading-tight" style={{ color: 'var(--text)' }}>
                              {app.role || '—'}
                            </div>
                            <div className="text-[10px] mt-0.5 flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                              <Building2 size={9} /> {app.company || '—'}
                            </div>
                          </div>
                        </div>

                        {/* Source badge */}
                        {app.source && (
                          <span className="badge badge-neutral" style={{ fontSize: 9 }}>
                            {app.source}
                          </span>
                        )}

                        {/* Follow-up date */}
                        {app.follow_up_date && (
                          <div className="mt-1.5 flex items-center gap-1 text-[10px]" style={{ color: 'var(--amber)' }}>
                            <Clock size={9} /> {formatDate(app.follow_up_date)}
                          </div>
                        )}

                        {/* Open link (hover) */}
                        {app.job_url && (
                          <a
                            href={app.job_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1.5 text-[10px] flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                            style={{ color: 'var(--primary)' }}
                          >
                            <ExternalLink size={9} /> Open listing
                          </a>
                        )}
                      </motion.div>
                    ))}

                    {cards.length === 0 && (
                      <div
                        className="rounded-lg border-2 border-dashed p-4 text-center"
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