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
import { Skeleton } from '@/components/ui/Skeleton';

interface Props {
  jobId: number | null;
  onClose: () => void;
}

const TABS = ['overview', 'skills', 'email', 'recruiter'] as const;
type Tab = typeof TABS[number];

export default function JobDetailDrawer({ jobId, onClose }: Props) {
  const [job, setJob] = useState<any>(null);
  const [match, setMatch] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    setActiveTab('overview');
    setJob(null);
    setMatch(null);
    Promise.all([
      getJobDetail(jobId).then(r => setJob(r.job)),
      getJobMatch(jobId).then(r => setMatch(r.match)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [jobId, onClose]);

  const copyEmail = () => {
    if (!job?.email_body) return;
    navigator.clipboard.writeText(job.email_body);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const visibleTabs = TABS.filter(t => {
    if (t === 'overview') return true;
    if (t === 'skills')   return true;
    if (t === 'email')    return job?.email_body;
    if (t === 'recruiter')return job?.hr_email;
    return false;
  });

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
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(4px)' }}
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            id="job-detail-drawer"
            className="fixed right-0 top-0 h-full w-[520px] z-50 flex flex-col"
            style={{
              background: 'var(--bg)',
              borderLeft: '1px solid var(--border)',
              boxShadow: '-24px 0 72px rgba(0, 0, 0, 0.4)',
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
                id="drawer-close-btn"
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
                <div className="flex items-start gap-4">
                  <div className="shimmer w-12 h-12 rounded-xl" />
                  <div className="flex-1 space-y-2">
                    <div className="shimmer h-5 rounded w-3/4" />
                    <div className="shimmer h-4 rounded w-1/2" />
                  </div>
                </div>
                {[1, 2, 3].map(i => <Skeleton key={i} height={60} rounded="lg" />)}
              </div>
            ) : job ? (
              <div className="flex-1 overflow-y-auto">
                {/* Job Hero Header */}
                <div className="px-6 pt-6 pb-4">
                  <div className="flex items-start gap-4">
                    {/* Company avatar with gradient */}
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 text-lg font-bold text-white"
                      style={{
                        background: `linear-gradient(135deg, var(--primary), var(--accent))`,
                        boxShadow: '0 4px 16px rgba(124, 92, 252, 0.3)',
                      }}
                    >
                      {(job.company || '?')[0].toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="text-base font-bold leading-tight" style={{ color: 'var(--text)' }}>
                        {job.title || 'Untitled Role'}
                      </h2>
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        <span className="text-sm flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
                          <Building2 size={12} /> {job.company}
                        </span>
                        {job.location && (
                          <span className="text-sm flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                            <MapPin size={12} /> {job.location}
                          </span>
                        )}
                      </div>
                    </div>
                    {job.fit_score != null && (
                      <ScoreRing score={job.fit_score} size={52} strokeWidth={4} />
                    )}
                  </div>

                  {/* Glassmorphism stat chips */}
                  <div className="grid grid-cols-3 gap-2.5 mt-4">
                    {[
                      { icon: Globe,     label: 'Source', value: job.source || '—' },
                      { icon: DollarSign,label: 'Salary', value: job.salary || 'N/A' },
                      { icon: Clock,     label: 'Found',  value: formatDate(job.scraped_at) },
                    ].map((stat, i) => (
                      <div
                        key={i}
                        className="glass-surface p-2.5"
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

                  {/* Status + apply */}
                  <div className="flex items-center gap-2 mt-3">
                    <span className={`badge ${statusBadge(job.status || 'found')}`}>
                      {job.status || 'found'}
                    </span>
                    {job.job_url && (
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        id="apply-external-link"
                        className="btn btn-primary btn-sm ml-auto"
                      >
                        <ExternalLink size={11} /> Apply
                      </a>
                    )}
                  </div>
                </div>

                {/* Animated tab bar */}
                <div
                  className="px-6 flex items-center relative"
                  style={{ borderBottom: '1px solid var(--border)' }}
                >
                  {visibleTabs.map(tab => (
                    <button
                      key={tab}
                      id={`tab-${tab}`}
                      onClick={() => setActiveTab(tab)}
                      className="relative px-3 py-2.5 text-sm capitalize transition-colors"
                      style={{ color: activeTab === tab ? 'var(--text)' : 'var(--text-muted)' }}
                    >
                      {tab}
                      {activeTab === tab && (
                        <motion.div
                          layoutId="drawer-tab-indicator"
                          className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full"
                          style={{ background: 'var(--primary)' }}
                          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                        />
                      )}
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                <div className="px-6 py-5 space-y-4">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeTab}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                    >
                      {/* Overview */}
                      {activeTab === 'overview' && (
                        <>
                          {match && <MatchScoreCard match={match} />}
                          {job.jd_text && (
                            <div>
                              <div className="text-label mb-2 flex items-center gap-2">
                                <FileText size={11} /> Job Description
                              </div>
                              <div
                                className="text-xs leading-relaxed p-4 rounded-xl max-h-[280px] overflow-y-auto whitespace-pre-wrap"
                                style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}
                              >
                                {job.jd_text}
                              </div>
                            </div>
                          )}
                        </>
                      )}

                      {/* Skills */}
                      {activeTab === 'skills' && match && (
                        <div className="space-y-4">
                          {match.matched_skills?.length > 0 && (
                            <div>
                              <div className="text-label mb-2 flex items-center gap-2">
                                <CheckCircle2 size={11} style={{ color: 'var(--green)' }} /> Matched
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
                                <XCircle size={11} style={{ color: 'var(--red)' }} /> Missing
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
                              className="text-xs leading-relaxed p-4 rounded-xl"
                              style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}
                            >
                              {match.explanation}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Email */}
                      {activeTab === 'email' && job.email_body && (
                        <div>
                          <div
                            className="rounded-xl overflow-hidden"
                            style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
                          >
                            <div
                              className="px-4 py-2.5 space-y-0.5"
                              style={{ borderBottom: '1px solid var(--border)' }}
                            >
                              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                <strong>To:</strong> {job.hr_email || 'Not discovered'}
                              </div>
                              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                <strong>Subject:</strong> {job.email_subject || '—'}
                              </div>
                            </div>
                            <div
                              className="text-xs leading-relaxed whitespace-pre-wrap px-4 py-3"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              {job.email_body}
                            </div>
                          </div>
                          <button id="copy-email-body-btn" onClick={copyEmail} className="btn btn-secondary btn-sm mt-3">
                            <Copy size={12} />
                            {copied ? 'Copied!' : 'Copy email body'}
                          </button>
                        </div>
                      )}

                      {/* Recruiter */}
                      {activeTab === 'recruiter' && job.hr_email && (
                        <div
                          className="flex items-center gap-3 p-4 rounded-xl"
                          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                        >
                          <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
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
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>
            ) : null}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
