'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Rocket, Upload, FileText, Loader2, Sparkles, ShieldCheck, Mail } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import MissionControl from '@/components/pipeline/MissionControl';
import { runPipelineNow, uploadJD, pasteJD, getStatus } from '@/lib/api';

export default function PipelinePage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [jdText, setJdText] = useState('');
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
  }, []);

  const handleRunNow = useCallback(async () => {
    setRunning(true);
    try {
      const r = await runPipelineNow();
      if (r.run_id) setRunId(r.run_id);
    } catch {
      setRunning(false);
    }
  }, []);

  const handleUploadJD = useCallback(async (file: File) => {
    setRunning(true);
    try {
      const r = await uploadJD(file);
      if (r.run_id) setRunId(r.run_id);
    } catch {
      setRunning(false);
    }
  }, []);

  const handlePasteJD = useCallback(async () => {
    if (jdText.trim().length < 30) return;
    setRunning(true);
    try {
      const r = await pasteJD(jdText);
      if (r.run_id) setRunId(r.run_id);
    } catch {
      setRunning(false);
    }
  }, [jdText]);

  const handleComplete = useCallback(() => {
    setRunning(false);
  }, []);

  return (
    <Shell>
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(59,130,246,0.16), rgba(168,85,247,0.14) 45%, rgba(15,15,18,0.98) 100%)',
            borderColor: 'rgba(255,255,255,0.08)',
          }}
        >
          <div className="p-6 md:p-8 grid gap-6 md:grid-cols-[1.2fr_0.8fr] items-center">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                <Sparkles size={12} />
                Pipeline Mission Control
              </div>
              <div>
                <h1 className="text-3xl font-black tracking-tight" style={{ color: 'var(--text)' }}>Run the pipeline with one click.</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
                  Start full job discovery, run a specific JD, or drag in a posting and watch every step stream in real time.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleRunNow}
                  disabled={running}
                  className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
                  style={{ background: 'var(--accent)', color: '#fff' }}
                >
                  {running ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
                  {running ? 'Running pipeline...' : 'Run full pipeline'}
                </button>
                <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-xs border" style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.08)', color: 'var(--text-secondary)' }}>
                  <ShieldCheck size={14} style={{ color: 'var(--green)' }} />
                  {status?.resume_uploaded ? 'Resume connected' : 'Upload resume first'}
                </div>
                <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-xs border" style={{ background: 'rgba(255,255,255,0.03)', borderColor: 'rgba(255,255,255,0.08)', color: 'var(--text-secondary)' }}>
                  <Mail size={14} style={{ color: 'var(--amber)' }} />
                  {status?.email?.configured ? `Email ready via ${status.email.provider || 'provider'}` : 'Email needs configuration'}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Resume', value: status?.resume_uploaded ? 'Ready' : 'Missing', color: status?.resume_uploaded ? 'var(--green)' : 'var(--amber)' },
                { label: 'Email', value: status?.email?.configured ? 'Ready' : 'Needs setup', color: status?.email?.configured ? 'var(--green)' : 'var(--amber)' },
                { label: 'Apollo', value: status?.recruiter_discovery?.apollo ? 'Connected' : 'Off', color: status?.recruiter_discovery?.apollo ? 'var(--green)' : 'var(--text-muted)' },
                { label: 'Dry run', value: status?.dry_run ? 'On' : 'Off', color: 'var(--accent)' },
              ].map((item) => (
                <div key={item.label} className="rounded-2xl border p-4 backdrop-blur-sm" style={{ background: 'rgba(15,15,18,0.6)', borderColor: 'rgba(255,255,255,0.08)' }}>
                  <div className="text-[10px] uppercase tracking-[0.22em]" style={{ color: 'var(--text-muted)' }}>{item.label}</div>
                  <div className="mt-3 text-lg font-bold" style={{ color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        <MissionControl runId={runId} onComplete={handleComplete} />

        <div className="grid grid-cols-2 gap-5">
          <div className="rounded-2xl p-6 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Upload JD</div>
                <div className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>Drop a PDF, image, or text file to start a targeted run.</div>
              </div>
            </div>
            <div
              className="border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 hover:border-[var(--accent)] hover:bg-[var(--accent-muted)]"
              style={{ borderColor: 'var(--border)' }}
              onClick={() => document.getElementById('jd-file-input')?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file) handleUploadJD(file);
              }}
            >
              <Upload size={28} className="mx-auto mb-3" style={{ color: 'var(--accent)' }} />
              <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>Click or drag a JD file</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>PDF, PNG, JPG, TXT supported</p>
            </div>
            <input
              id="jd-file-input"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUploadJD(e.target.files[0])}
            />
          </div>

          <div className="rounded-2xl p-6 card-hover" style={{ background: 'var(--surface)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>Paste JD Text</div>
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={8}
              placeholder="Paste the full job description here..."
              className="w-full rounded-xl p-4 text-sm resize-none outline-none transition-colors"
              style={{ background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)', fontFamily: 'var(--sans)' }}
            />
            <button
              onClick={handlePasteJD}
              disabled={jdText.trim().length < 30 || running}
              className="w-full mt-3 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all duration-150 disabled:opacity-40"
              style={{ background: 'var(--accent)', color: '#fff' }}
            >
              <FileText size={14} />
              Run on this JD
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
