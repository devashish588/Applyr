'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Terminal, CheckCircle2, XCircle, Loader2, Clock,
  Search, FileText, BarChart3, Sparkles, Mail, Rocket,
  Building2, MessageSquareText, ClipboardCheck, CalendarClock, Users,
} from 'lucide-react';
import { createPipelineStream } from '@/lib/api';
import { formatTime } from '@/lib/utils';
import ProgressBar from '@/components/ui/ProgressBar';

interface LogEntry {
  step: string;
  msg: string;
  pct: number;
  agent?: string;
  status?: string;
  timestamp?: string;
  blocked?: boolean;
  validation?: {
    name: boolean;
    skills: boolean;
    experience: boolean;
    education: boolean;
    projects: boolean;
    confidence: number;
  };
}

const AGENT_ICONS: Record<string, any> = {
  orchestrator:        Rocket,
  web_research:        Search,
  resume_parser:       FileText,
  fit_scorer:          BarChart3,
  job_application:     Sparkles,
  email_drafting:      Mail,
  startup_discovery:   Building2,
  apollo:              Users,
  outreach:            MessageSquareText,
  application_tracker: ClipboardCheck,
  followup_scheduler:  CalendarClock,
};

const AGENT_COLORS: Record<string, string> = {
  orchestrator:        'var(--primary)',
  web_research:        'var(--accent)',
  resume_parser:       'var(--amber)',
  fit_scorer:          'var(--green)',
  job_application:     'var(--primary)',
  email_drafting:      'var(--accent)',
  startup_discovery:   'var(--primary)',
  apollo:              'var(--accent)',
  outreach:            'var(--green)',
  application_tracker: 'var(--amber)',
  followup_scheduler:  'var(--green)',
};

const AGENT_LOG_CLASS: Record<string, string> = {
  orchestrator:        'log-border-primary',
  web_research:        'log-border-accent',
  resume_parser:       'log-border-amber',
  fit_scorer:          'log-border-green',
  job_application:     'log-border-primary',
  email_drafting:      'log-border-accent',
  startup_discovery:   'log-border-primary',
  apollo:              'log-border-accent',
  outreach:            'log-border-green',
  application_tracker: 'log-border-amber',
  followup_scheduler:  'log-border-green',
};

const MILESTONE_STEPS = [
  'startup_discovered', 'company_matched', 'recruiter_found',
  'linkedin_message_generated', 'resume_tailored', 'ats_score_calculated',
  'careers_application_submitted', 'followup_scheduled',
];

interface Props {
  runId: string | null;
  onComplete?: () => void;
  onLogEntry?: (step: string) => void;
}

export default function MissionControl({ runId, onComplete, onLogEntry }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!runId) return;
    setLogs([]);
    setProgress(0);
    setStatus('running');

    const es = createPipelineStream(runId);

    es.onmessage = (e) => {
      const data: LogEntry = JSON.parse(e.data);
      setLogs(prev => [...prev, data]);
      setProgress(data.pct || 0);
      onLogEntry?.(data.step);

      if (data.step === 'blocked') { setStatus('error'); onComplete?.(); es.close(); }
      if (data.step === 'done')    { setStatus('done');  onComplete?.(); es.close(); }
      if (data.step === 'error')   { setStatus('error'); es.close(); }
    };

    es.onerror = () => { setStatus('error'); es.close(); };
    return () => es.close();
  }, [runId, onComplete, onLogEntry]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!runId && status === 'idle') return null;

  const statusConfig = {
    running: { badge: 'badge-primary', icon: Loader2,      label: 'Running',  iconClass: 'animate-spin', progressColor: 'var(--primary)' },
    done:    { badge: 'badge-green',   icon: CheckCircle2, label: 'Complete', iconClass: '',             progressColor: 'var(--green)' },
    error:   { badge: 'badge-red',     icon: XCircle,      label: 'Error',    iconClass: '',             progressColor: 'var(--red)' },
    idle:    { badge: 'badge-neutral', icon: Clock,        label: 'Idle',     iconClass: '',             progressColor: 'var(--text-faint)' },
  }[status];

  const StatusIcon = statusConfig.icon;
  const milestones = logs.filter(l => MILESTONE_STEPS.includes(l.step));

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, height: 'auto', opacity: 1 }}
      className="card overflow-hidden"
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-2">
          <Terminal size={13} style={{ color: 'var(--primary)' }} />
          <span className="text-label">Live Stream</span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="text-xs tabular-nums font-mono"
            style={{ color: 'var(--text-muted)' }}
          >
            {Math.round(progress)}%
          </span>
          <span className={`badge ${statusConfig.badge}`}>
            <StatusIcon size={10} className={statusConfig.iconClass} />
            {statusConfig.label}
          </span>
        </div>
      </div>

      {/* Gradient progress bar */}
      <div style={{ height: 3, background: 'var(--surface-2)', position: 'relative', overflow: 'hidden' }}>
        <motion.div
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          style={{
            position: 'absolute',
            inset: '0 auto 0 0',
            background: status === 'error'
              ? 'var(--red)'
              : status === 'done'
              ? 'linear-gradient(90deg, var(--green), var(--accent))'
              : 'linear-gradient(90deg, var(--primary), var(--accent))',
          }}
        />
      </div>

      {/* Log stream */}
      <div
        className="max-h-[300px] overflow-y-auto p-4 space-y-0.5"
        style={{ background: 'var(--bg)', fontFamily: 'var(--font-mono)' }}
      >
        <AnimatePresence>
          {logs.map((log, i) => {
            const Icon  = AGENT_ICONS[log.agent || ''] || Clock;
            const color = AGENT_COLORS[log.agent || ''] || 'var(--text-muted)';
            const borderClass = AGENT_LOG_CLASS[log.agent || ''] || 'log-border-muted';

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex items-start gap-3 py-1.5 px-3 rounded-md text-xs log-line ${borderClass}`}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <span className="text-[10px] shrink-0 pt-0.5 tabular-nums" style={{ color: 'var(--text-faint)' }}>
                  {formatTime(log.timestamp)}
                </span>
                <Icon size={11} className="shrink-0 mt-0.5" style={{ color }} />
                <span style={{ color: log.step === 'error' ? 'var(--red)' : 'var(--text-secondary)' }}>
                  {log.msg}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={logEndRef} />
      </div>

      {/* Blocked resume card */}
      {logs.some(l => l.step === 'blocked') && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-5 mb-5 mt-2 p-4 rounded-xl"
          style={{
            background: 'var(--red-subtle)',
            border: '1px solid rgba(248, 113, 113, 0.2)',
          }}
        >
          <div className="flex items-center gap-2 mb-3">
            <XCircle size={14} style={{ color: 'var(--red)' }} />
            <h4 className="font-semibold text-sm" style={{ color: 'var(--red)' }}>
              Resume Parsing Failed
            </h4>
          </div>

          {logs[0]?.validation && (
            <div className="space-y-1.5 mb-3">
              {[
                ['Name',       logs[0].validation.name],
                ['Skills',     logs[0].validation.skills],
                ['Experience', logs[0].validation.experience],
                ['Education',  logs[0].validation.education],
                ['Projects',   logs[0].validation.projects],
              ].map(([label, ok]) => (
                <div
                  key={String(label)}
                  className="flex items-center justify-between text-xs py-1"
                  style={{ borderBottom: '1px solid rgba(248, 113, 113, 0.12)' }}
                >
                  <span style={{ color: 'var(--text-secondary)' }}>{label as string}</span>
                  <span className={`badge ${ok ? 'badge-green' : 'badge-red'}`}>{ok ? 'Parsed' : 'Failed'}</span>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
            {logs[0]?.msg || 'Resume validation failed'}
          </p>

          <button
            id="upload-different-resume-btn"
            onClick={() => document.getElementById('resume-file-input')?.click()}
            className="btn btn-danger btn-sm w-full"
          >
            Upload a different resume
          </button>
        </motion.div>
      )}

      {/* Milestones timeline */}
      {milestones.length > 0 && (
        <div className="px-5 pb-5">
          <div
            className="rounded-xl p-4"
            style={{ background: 'var(--primary-subtle)', border: '1px solid rgba(124,92,252,0.12)' }}
          >
            <div className="text-label mb-3">Workflow Milestones</div>
            <div className="relative pl-5">
              {/* Vertical timeline line */}
              <div
                className="absolute left-1.5 top-0 bottom-0 w-px"
                style={{ background: 'linear-gradient(to bottom, var(--primary), transparent)' }}
              />
              <div className="space-y-2.5 max-h-[200px] overflow-y-auto">
                {[...milestones].reverse().map((log, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex items-start gap-2.5 text-xs"
                  >
                    <CheckCircle2
                      size={12}
                      className="shrink-0 mt-0.5"
                      style={{ color: 'var(--primary)' }}
                    />
                    <div>
                      <div style={{ color: 'var(--text)' }}>{log.msg}</div>
                      <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                        {log.agent || 'orchestrator'}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
