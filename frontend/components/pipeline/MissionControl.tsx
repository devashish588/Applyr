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
  orchestrator: Rocket,
  web_research: Search,
  resume_parser: FileText,
  fit_scorer: BarChart3,
  job_application: Sparkles,
  email_drafting: Mail,
  startup_discovery: Building2,
  apollo: Users,
  outreach: MessageSquareText,
  application_tracker: ClipboardCheck,
  followup_scheduler: CalendarClock,
};

const AGENT_COLORS: Record<string, string> = {
  orchestrator: 'var(--accent)',
  web_research: 'var(--purple)',
  resume_parser: 'var(--amber)',
  fit_scorer: 'var(--green)',
  job_application: 'var(--accent)',
  email_drafting: 'var(--purple)',
  startup_discovery: 'var(--accent)',
  apollo: 'var(--purple)',
  outreach: 'var(--green)',
  application_tracker: 'var(--amber)',
  followup_scheduler: 'var(--green)',
};

interface Props {
  runId: string | null;
  onComplete?: () => void;
}

export default function MissionControl({ runId, onComplete }: Props) {
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

      if (data.step === 'blocked') {
        setStatus('error');
        onComplete?.();
        es.close();
      }
      if (data.step === 'done') {
        setStatus('done');
        onComplete?.();
        es.close();
      }
      if (data.step === 'error') {
        setStatus('error');
        es.close();
      }
    };

    es.onerror = () => {
      setStatus('error');
      es.close();
    };

    return () => es.close();
  }, [runId, onComplete]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!runId && status === 'idle') return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      className="rounded-xl overflow-hidden card-hover"
      style={{ background: 'var(--surface)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b"
           style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <Terminal size={14} style={{ color: 'var(--accent)' }} />
          <span className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-muted)' }}>
            Mission Control
          </span>
        </div>
        <div className="flex items-center gap-2">
          {status === 'running' && (
            <span className="flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>
              <Loader2 size={10} className="animate-spin" />
              Running
            </span>
          )}
          {status === 'done' && (
            <span className="flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--green-muted)', color: 'var(--green)' }}>
              <CheckCircle2 size={10} />
              Complete
            </span>
          )}
          {status === 'error' && (
            <span className="flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--red-muted)', color: 'var(--red)' }}>
              <XCircle size={10} />
              Error
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1" style={{ background: 'var(--border)' }}>
        <motion.div
          className="h-full rounded-r"
          style={{
            background: status === 'error' ? 'var(--red)' :
                       status === 'done' ? 'var(--green)' : 'var(--accent)',
          }}
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>

      {/* Log entries */}
      <div className="max-h-[320px] overflow-y-auto p-4 font-mono text-xs space-y-1"
           style={{ background: 'var(--bg)' }}>
        <AnimatePresence>
          {logs.map((log, i) => {
            const Icon = AGENT_ICONS[log.agent || ''] || Clock;
            const color = AGENT_COLORS[log.agent || ''] || 'var(--text-muted)';

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-start gap-3 py-1.5 px-2 rounded hover:bg-white/[0.02]"
              >
                <span className="text-[10px] shrink-0 pt-0.5 tabular-nums"
                      style={{ color: 'var(--text-muted)' }}>
                  {formatTime(log.timestamp)}
                </span>
                <Icon size={12} className="shrink-0 mt-0.5" style={{ color }} />
                <span style={{ color: log.step === 'error' ? 'var(--red)' : 'var(--text-secondary)' }}>
                  {log.msg}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={logEndRef} />
      </div>

      {/* Blocked Resume Card */}
      {logs.some(l => l.step === 'blocked') && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-5 mb-5 mt-4 p-4 rounded-lg border"
          style={{ 
            borderColor: 'rgba(239, 68, 68, 0.3)',
            background: 'rgba(239, 68, 68, 0.06)'
          }}
        >
          <div className="flex items-center gap-2 mb-3">
            <XCircle size={16} style={{ color: 'var(--red)' }} />
            <h4 className="font-semibold text-sm" style={{ color: 'var(--red)' }}>
              Resume Parsing Failed
            </h4>
          </div>
          
          {/* Validation Checklist */}
          {logs[0]?.validation && (
            <div className="space-y-2 mb-3">
              <ValidationRow label="Name" ok={logs[0].validation.name} />
              <ValidationRow label="Skills" ok={logs[0].validation.skills} />
              <ValidationRow label="Experience" ok={logs[0].validation.experience} />
              <ValidationRow label="Education" ok={logs[0].validation.education} />
              <ValidationRow label="Projects" ok={logs[0].validation.projects} />
              <div className="flex justify-between items-center pt-2 border-t"
                   style={{ borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Confidence Score
                </span>
                <span className="font-semibold text-sm" style={{ color: 'var(--red)' }}>
                  {logs[0].validation.confidence}%
                </span>
              </div>
            </div>
          )}

          {/* Error Message */}
          <p className="text-xs leading-relaxed mb-3"
             style={{ color: 'var(--text-secondary)' }}>
            {logs[0]?.msg || 'Resume validation failed'}
          </p>

          <button
            onClick={() => document.getElementById('resume-file-input')?.click()}
            className="w-full text-xs font-medium py-2 px-3 rounded-lg transition-colors"
            style={{
              background: 'rgba(239, 68, 68, 0.15)',
              color: 'var(--red)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
            }}
          >
            Upload a different resume
          </button>
        </motion.div>
      )}

      {logs.some(l => ['startup_discovered', 'company_matched', 'recruiter_found', 'linkedin_message_generated', 'resume_tailored', 'ats_score_calculated', 'careers_application_submitted', 'followup_scheduled'].includes(l.step)) && (
        <div className="px-5 pb-5">
          <div className="rounded-xl p-4 border" style={{ background: 'rgba(59,130,246,0.06)', borderColor: 'rgba(59,130,246,0.18)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>Workflow timeline</div>
            <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
              {[...logs].reverse().map((log, idx) => (
                ['startup_discovered', 'company_matched', 'recruiter_found', 'linkedin_message_generated', 'resume_tailored', 'ats_score_calculated', 'careers_application_submitted', 'followup_scheduled'].includes(log.step) ? (
                  <div key={idx} className="flex items-start gap-3 text-xs py-1">
                    <Clock size={12} style={{ color: 'var(--text-muted)', marginTop: 2 }} />
                    <div>
                      <div style={{ color: 'var(--text)' }}>{log.msg}</div>
                      <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{log.agent || 'orchestrator'}</div>
                    </div>
                  </div>
                ) : null
              ))}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}

// Helper component for validation checklist
function ValidationRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between text-xs px-0 py-1.5"
         style={{ borderBottom: '1px solid rgba(239, 68, 68, 0.2)' }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span className="font-medium"
            style={{ color: ok ? 'var(--green)' : 'var(--red)' }}>
        {ok ? '✓ Parsed' : '✗ Failed'}
      </span>
    </div>
  );
}
