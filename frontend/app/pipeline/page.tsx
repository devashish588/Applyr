'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Rocket, Upload, FileText, Loader2, ChevronRight } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import MissionControl from '@/components/pipeline/MissionControl';
import { runPipelineNow, uploadJD, pasteJD, getStatus } from '@/lib/api';

const PIPELINE_STAGES = [
  'Resume', 'Query', 'Scrape', 'Rank', 'Recruit', 'Tailor', 'Email', 'Ready'
];

export default function PipelinePage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [jdText, setJdText] = useState('');
  const [status, setStatus] = useState<any>(null);

  useEffect(() => { getStatus().then(setStatus).catch(() => {}); }, []);

  const handleRunNow = useCallback(async () => {
    setRunning(true);
    try { const r = await runPipelineNow(); if (r.run_id) setRunId(r.run_id); } catch { setRunning(false); }
  }, []);

  const handleUploadJD = useCallback(async (file: File) => {
    setRunning(true);
    try { const r = await uploadJD(file); if (r.run_id) setRunId(r.run_id); } catch { setRunning(false); }
  }, []);

  const handlePasteJD = useCallback(async () => {
    if (jdText.trim().length < 30) return;
    setRunning(true);
    try { const r = await pasteJD(jdText); if (r.run_id) setRunId(r.run_id); } catch { setRunning(false); }
  }, [jdText]);

  const handleComplete = useCallback(() => setRunning(false), []);

  return (
    <Shell>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Mission Control</h1>
            <p className="text-body mt-0.5">Run the pipeline, upload a JD, or paste a job posting.</p>
          </div>
          <button onClick={handleRunNow} disabled={running} className="btn btn-primary">
            {running ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />}
            {running ? 'Running...' : 'Run Pipeline'}
          </button>
        </div>

        {/* Pipeline Stages — flat, no card wrapper */}
        <div>
          <div className="text-label mb-3">Pipeline Stages</div>
          <div className="flex items-center">
            {PIPELINE_STAGES.map((stage, i) => (
              <div key={stage} className="flex items-center">
                <div className="text-center">
                  <div
                    className="mx-auto w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold tabular-nums mb-1"
                    style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
                  >
                    {i + 1}
                  </div>
                  <div className="text-[10px]" style={{ color: 'var(--text-faint)' }}>{stage}</div>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div className="w-6 flex items-center justify-center" style={{ marginBottom: 14 }}>
                    <ChevronRight size={9} style={{ color: 'var(--text-faint)' }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Readiness — flat inline, no cards */}
        <div className="flex items-center gap-6">
          {[
            { label: 'Resume', ready: status?.resume_uploaded },
            { label: 'Email', ready: status?.email?.configured },
            { label: 'Apollo', ready: status?.recruiter_discovery?.apollo },
            { label: 'Mode', ready: true, value: status?.dry_run ? 'Sandbox' : 'Live' },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: item.ready ? 'var(--green)' : 'var(--amber)' }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
              <span className="text-xs" style={{ color: item.ready ? 'var(--green)' : 'var(--amber)' }}>
                {item.value || (item.ready ? 'Ready' : 'Missing')}
              </span>
            </div>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Mission Control Stream — this one gets a card because it's an independent object */}
        <MissionControl runId={runId} onComplete={handleComplete} />

        {/* Upload / Paste — side by side, minimal containers */}
        <div className="grid grid-cols-2 gap-8">
          <div>
            <div className="text-label mb-2">Upload JD</div>
            <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
              Drop a PDF, image, or text file for a targeted run.
            </p>
            <div
              className="border border-dashed rounded-lg p-6 text-center cursor-pointer transition-all"
              style={{ borderColor: 'var(--border)' }}
              onClick={() => document.getElementById('jd-file-input')?.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleUploadJD(f); }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-hover)'; e.currentTarget.style.background = 'var(--surface-hover)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'transparent'; }}
            >
              <Upload size={18} className="mx-auto mb-1" style={{ color: 'var(--text-muted)' }} />
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Click or drag a file</p>
              <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>PDF, PNG, JPG, TXT</p>
            </div>
            <input id="jd-file-input" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" className="hidden"
              onChange={e => e.target.files?.[0] && handleUploadJD(e.target.files[0])} />
          </div>

          <div>
            <div className="text-label mb-2">Paste JD</div>
            <textarea
              value={jdText}
              onChange={e => setJdText(e.target.value)}
              rows={5}
              placeholder="Paste the full job description..."
              className="input"
              style={{ minHeight: 112, resize: 'none' }}
            />
            <button onClick={handlePasteJD} disabled={jdText.trim().length < 30 || running} className="btn btn-primary btn-sm w-full mt-2">
              <FileText size={12} /> Run on this JD
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
