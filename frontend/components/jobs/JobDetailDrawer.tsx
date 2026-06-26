'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Briefcase, Building2, MapPin, Globe, DollarSign,
  BarChart3, Mail, User, FileText, Sparkles, Clock,
} from 'lucide-react';
import { getJobDetail, getJobMatch } from '@/lib/api';
import { getScoreColor, formatDate } from '@/lib/utils';
import MatchScoreCard from './MatchScoreCard';

interface Props {
  jobId: number | null;
  onClose: () => void;
}

export default function JobDetailDrawer({ jobId, onClose }: Props) {
  const [job, setJob] = useState<any>(null);
  const [match, setMatch] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    Promise.all([
      getJobDetail(jobId).then(r => setJob(r.job)),
      getJobMatch(jobId).then(r => setMatch(r.match)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [jobId]);

  return (
    <AnimatePresence>
      {jobId !== null && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.5)' }}
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 h-full w-[480px] z-50 overflow-y-auto border-l"
            style={{ background: 'var(--bg)', borderColor: 'var(--border)' }}
          >
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 border-b glass"
                 style={{ borderColor: 'var(--border)' }}>
              <span className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                Job Details
              </span>
              <button
                onClick={onClose}
                className="p-1.5 rounded-md transition-colors hover:bg-white/5"
              >
                <X size={16} style={{ color: 'var(--text-muted)' }} />
              </button>
            </div>

            {loading ? (
              <div className="p-6 space-y-4">
                {[1,2,3].map(i => (
                  <div key={i} className="h-16 rounded-lg shimmer" />
                ))}
              </div>
            ) : job ? (
              <div className="p-6 space-y-5">
                {/* Title */}
                <div>
                  <h2 className="text-lg font-bold mb-1" style={{ color: 'var(--text)' }}>
                    {job.title || 'Untitled Role'}
                  </h2>
                  <div className="flex items-center gap-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                    <span className="flex items-center gap-1">
                      <Building2 size={13} />
                      {job.company}
                    </span>
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin size={13} />
                        {job.location}
                      </span>
                    )}
                  </div>
                </div>

                {/* Quick stats */}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { icon: Globe, label: 'Source', value: job.source || '—' },
                    { icon: DollarSign, label: 'Salary', value: job.salary || 'Not specified' },
                    { icon: BarChart3, label: 'Fit Score', value: job.fit_score ? `${job.fit_score}%` : '—',
                      color: job.fit_score ? getScoreColor(job.fit_score) : undefined },
                    { icon: Clock, label: 'Found', value: formatDate(job.scraped_at) },
                  ].map((stat, i) => (
                    <div key={i} className="p-3 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                      <div className="flex items-center gap-1.5 mb-1">
                        <stat.icon size={11} style={{ color: 'var(--text-muted)' }} />
                        <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                          {stat.label}
                        </span>
                      </div>
                      <span className="text-sm font-semibold" style={{ color: stat.color || 'var(--text)' }}>
                        {stat.value}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Status */}
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                    Status
                  </span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                        style={{
                          background: job.status === 'sent' ? 'var(--green-muted)' :
                                     job.status === 'draft' ? 'var(--accent-muted)' :
                                     job.status === 'skipped' ? 'var(--red-muted)' : 'var(--surface-2)',
                          color: job.status === 'sent' ? 'var(--green)' :
                                job.status === 'draft' ? 'var(--accent)' :
                                job.status === 'skipped' ? 'var(--red)' : 'var(--text-muted)',
                        }}>
                    {job.status || 'found'}
                  </span>
                </div>

                {/* Match breakdown */}
                {match && <MatchScoreCard match={match} />}

                {/* Job Description */}
                {job.jd_text && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <FileText size={12} style={{ color: 'var(--text-muted)' }} />
                      <span className="text-[10px] uppercase tracking-wider font-semibold"
                            style={{ color: 'var(--text-muted)' }}>
                        Job Description
                      </span>
                    </div>
                    <div className="text-xs leading-relaxed p-3 rounded-lg max-h-[200px] overflow-y-auto"
                         style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
                      {job.jd_text}
                    </div>
                  </div>
                )}

                {/* Email Draft */}
                {job.email_body && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Mail size={12} style={{ color: 'var(--purple)' }} />
                      <span className="text-[10px] uppercase tracking-wider font-semibold"
                            style={{ color: 'var(--text-muted)' }}>
                        Email Draft
                      </span>
                    </div>
                    <div className="p-3 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                      <div className="text-[11px] mb-2" style={{ color: 'var(--text-muted)' }}>
                        <strong>To:</strong> {job.hr_email || 'Not discovered'}
                      </div>
                      <div className="text-[11px] mb-2" style={{ color: 'var(--text-muted)' }}>
                        <strong>Subject:</strong> {job.email_subject || '—'}
                      </div>
                      <div className="text-xs leading-relaxed whitespace-pre-wrap max-h-[150px] overflow-y-auto"
                           style={{ color: 'var(--text-secondary)' }}>
                        {job.email_body}
                      </div>
                    </div>
                  </div>
                )}

                {/* Recruiter */}
                {job.hr_email && (
                  <div className="flex items-center gap-2 p-3 rounded-lg"
                       style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                    <User size={14} style={{ color: 'var(--accent)' }} />
                    <div>
                      <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                        Recruiter
                      </div>
                      <div className="text-xs font-mono" style={{ color: 'var(--text)' }}>
                        {job.hr_email}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
