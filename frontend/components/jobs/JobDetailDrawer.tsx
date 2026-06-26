'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Building2, MapPin, Globe, DollarSign, BarChart3, Mail,
  User, FileText, Clock, CheckCircle2, XCircle, Copy, ExternalLink,
} from 'lucide-react';
import { getJobDetail, getJobMatch } from '@/lib/api';
import { getScoreColor, formatDate } from '@/lib/utils';
import MatchScoreCard from './MatchScoreCard';
import ScoreRing from '@/components/ui/ScoreRing';
import Tabs from '@/components/ui/Tabs';
import { Skeleton } from '@/components/ui/Skeleton';

interface Props {
  jobId: number | null;
  onClose: () => void;
}

export default function JobDetailDrawer({ jobId, onClose }: Props) {
  const [job, setJob] = useState<any>(null);
  const [match, setMatch] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    setActiveTab('overview');
    Promise.all([
      getJobDetail(jobId).then(r => setJob(r.job)),
      getJobMatch(jobId).then(r => setMatch(r.match)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [jobId, onClose]);

  const copyEmail = () => {
    if (!job?.email_body) return;
    navigator.clipboard.writeText(job.email_body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'skills', label: 'Skills' },
    ...(job?.email_body ? [{ id: 'email', label: 'Email' }] : []),
    ...(job?.hr_email ? [{ id: 'recruiter', label: 'Recruiter' }] : []),
  ];

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      sent: 'badge-green', draft: 'badge-blue', ready: 'badge-amber',
      skipped: 'badge-red', found: 'badge-neutral',
    };
    return map[status] || 'badge-neutral';
  };

  return (
    <AnimatePresence>
      {jobId !== null && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0, 0, 0, 0.5)' }}
            onClick={onClose}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-[520px] z-50 flex flex-col"
            style={{
              background: 'var(--bg)',
              borderLeft: '1px solid var(--border)',
              boxShadow: '-20px 0 60px rgba(0, 0, 0, 0.3)',
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-6 py-3.5 shrink-0 glass"
              style={{ borderBottom: '1px solid var(--border)' }}
            >
              <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                Job Details
              </span>
              <button
                onClick={onClose}
                className="w-7 h-7 rounded-md flex items-center justify-center transition-colors"
                style={{ color: 'var(--text-muted)' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-2)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <X size={15} />
              </button>
            </div>

            {loading ? (
              <div className="p-6 space-y-4">
                {[1, 2, 3].map(i => <Skeleton key={i} height={60} rounded="lg" />)}
              </div>
            ) : job ? (
              <div className="flex-1 overflow-y-auto">
                {/* Job Header */}
                <div className="px-6 pt-5 pb-4">
                  <div className="flex items-start gap-4">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 text-lg font-bold"
                      style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
                    >
                      {(job.company || '?')[0].toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="text-lg font-bold leading-tight" style={{ color: 'var(--text)' }}>
                        {job.title || 'Untitled Role'}
                      </h2>
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        <span className="text-sm flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
                          <Building2 size={13} /> {job.company}
                        </span>
                        {job.location && (
                          <span className="text-sm flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                            <MapPin size={13} /> {job.location}
                          </span>
                        )}
                      </div>
                    </div>
                    {job.fit_score != null && (
                      <ScoreRing score={job.fit_score} size={52} strokeWidth={4} />
                    )}
                  </div>

                  {/* Quick stats */}
                  <div className="grid grid-cols-3 gap-2.5 mt-4">
                    {[
                      { icon: Globe, label: 'Source', value: job.source || '—' },
                      { icon: DollarSign, label: 'Salary', value: job.salary || 'N/A' },
                      { icon: Clock, label: 'Found', value: formatDate(job.scraped_at) },
                    ].map((stat, i) => (
                      <div
                        key={i}
                        className="rounded-lg p-2.5"
                        style={{ background: 'var(--surface)', border: '1px solid var(--border-subtle)' }}
                      >
                        <div className="flex items-center gap-1 mb-1">
                          <stat.icon size={10} style={{ color: 'var(--text-faint)' }} />
                          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>
                            {stat.label}
                          </span>
                        </div>
                        <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>
                          {stat.value}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Status badge */}
                  <div className="flex items-center gap-2 mt-3">
                    <span className={`badge ${statusBadge(job.status || 'found')}`}>
                      {job.status || 'found'}
                    </span>
                  </div>
                </div>

                {/* Tabs */}
                <div className="px-6">
                  <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
                </div>

                {/* Tab Content */}
                <div className="px-6 py-4 space-y-4">
                  {activeTab === 'overview' && (
                    <>
                      {match && <MatchScoreCard match={match} />}
                      {job.jd_text && (
                        <div>
                          <div className="text-label mb-2 flex items-center gap-2">
                            <FileText size={11} /> Job Description
                          </div>
                          <div
                            className="text-xs leading-relaxed p-4 rounded-lg max-h-[280px] overflow-y-auto whitespace-pre-wrap"
                            style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}
                          >
                            {job.jd_text}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {activeTab === 'skills' && match && (
                    <div className="space-y-4">
                      {match.matched_skills?.length > 0 && (
                        <div>
                          <div className="text-label mb-2 flex items-center gap-2">
                            <CheckCircle2 size={11} style={{ color: 'var(--green)' }} /> Matched Skills
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {match.matched_skills.map((s: string, i: number) => (
                              <span key={i} className="badge badge-green">{s}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {match.missing_skills?.length > 0 && (
                        <div>
                          <div className="text-label mb-2 flex items-center gap-2">
                            <XCircle size={11} style={{ color: 'var(--red)' }} /> Missing Skills
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {match.missing_skills.map((s: string, i: number) => (
                              <span key={i} className="badge badge-red">{s}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {match.explanation && (
                        <div
                          className="text-xs leading-relaxed p-3 rounded-lg"
                          style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}
                        >
                          {match.explanation}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'email' && job.email_body && (
                    <div>
                      <div className="rounded-lg p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border-subtle)' }}>
                        <div className="text-[11px] mb-1" style={{ color: 'var(--text-muted)' }}>
                          <strong>To:</strong> {job.hr_email || 'Not discovered'}
                        </div>
                        <div className="text-[11px] mb-3" style={{ color: 'var(--text-muted)' }}>
                          <strong>Subject:</strong> {job.email_subject || '—'}
                        </div>
                        <div
                          className="text-xs leading-relaxed whitespace-pre-wrap"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {job.email_body}
                        </div>
                      </div>
                      <button onClick={copyEmail} className="btn btn-secondary btn-sm mt-3">
                        <Copy size={12} />
                        {copied ? 'Copied!' : 'Copy email body'}
                      </button>
                    </div>
                  )}

                  {activeTab === 'recruiter' && job.hr_email && (
                    <div
                      className="flex items-center gap-3 p-4 rounded-lg"
                      style={{ background: 'var(--surface)', border: '1px solid var(--border-subtle)' }}
                    >
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ background: 'var(--primary-muted)' }}
                      >
                        <User size={16} style={{ color: 'var(--primary)' }} />
                      </div>
                      <div>
                        <div className="text-label mb-0.5">Recruiter Contact</div>
                        <div className="text-sm font-mono" style={{ color: 'var(--text)' }}>
                          {job.hr_email}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
