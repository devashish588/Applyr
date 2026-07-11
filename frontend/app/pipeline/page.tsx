'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Rocket, Upload, FileText, Loader2 } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import MissionControl from '@/components/pipeline/MissionControl';
import PipelineNode, { type NodeStatus } from '@/components/ui/PipelineNode';
import { runPipelineNow, uploadJD, pasteJD, getStatus } from '@/lib/api';
import {
  Search, FileText as FileTextIcon, BarChart2, Users,
  Sparkles, Mail, Building2, CheckCircle2,
} from 'lucide-react';

const PIPELINE_STAGES = [
  { id: 'Resume',  icon: FileTextIcon },
  { id: 'Query',   icon: Search },
  { id: 'Scrape',  icon: FileTextIcon },
  { id: 'Rank',    icon: BarChart2 },
  { id: 'Recruit', icon: Users },
  { id: 'Tailor',  icon: Sparkles },
  { id: 'Email',   icon: Mail },
  { id: 'Ready',   icon: CheckCircle2 },
];

// Map pipeline log step → stage index
const STEP_TO_STAGE: Record<string, number> = {
  'resume_parsed': 0,
  'query_built': 1,
  'jobs_scraped': 2,
  'jobs_ranked': 3,
  'recruiters_found': 4,
  'resume_tailored': 5,
  'emails_drafted': 6,
  'done': 7,
};

export default function PipelinePage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [jdText, setJdText] = useState('');
  const [status, setStatus] = useState<any>(null);
  const [activeStage, setActiveStage] = useState<number>(-1);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => { getStatus().then(setStatus).catch(() => {}); }, []);

  // Listen for pipeline events to animate stages
  const handleLogEntry = useCallback((step: string) => {
    const idx = STEP_TO_STAGE[step];
    if (idx !== undefined) setActiveStage(idx);
  }, []);

  const getNodeStatus = (index: number): NodeStatus => {
    if (!running && activeStage === -1) return 'idle';
    if (index < activeStage) return 'complete';
    if (index === activeStage) return running ? 'active' : 'complete';
    return 'idle';
  };

  const handleRunNow = useCallback(async () => {
    setRunning(true);
    setActiveStage(0);
    try {
      const r = await runPipelineNow();
      if (r.run_id) setRunId(r.run_id);
    } catch { setRunning(false); }
  }, []);

  const handleUploadJD = useCallback(async (file: File) => {
    setRunning(true);
    setActiveStage(0);
    try {
      const r = await uploadJD(file);
      if (r.run_id) setRunId(r.run_id);
    } catch { setRunning(false); }
  }, []);

  const handlePasteJD = useCallback(async () => {
    if (jdText.trim().length < 30) return;
    setRunning(true);
    setActiveStage(0);
    try {
      const r = await pasteJD(jdText);
      if (r.run_id) setRunId(r.run_id);
    } catch { setRunning(false); }
  }, [jdText]);

  const handleComplete = useCallback(() => {
    setRunning(false);
    setActiveStage(7);
  }, []);

  const readinessItems = [
    { label: 'Resume',  ready: status?.resume_uploaded },
    { label: 'Email',   ready: status?.email?.configured },
    { label: 'Apollo',  ready: status?.recruiter_discovery?.apollo },
    { label: 'Mode',    ready: true, value: status?.dry_run ? 'Sandbox' : 'Live' },
  ];

  return (
    <Shell>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Mission Control</h1>
            <p className="text-body mt-0.5">Run the pipeline, upload a JD, or paste a job posting.</p>
          </div>
          <button
            id="run-pipeline-btn"
            onClick={handleRunNow}
            disabled={running}
            className={`btn btn-lg ${running ? 'btn-running' : 'btn-primary'}`}
          >
            {running
              ? <><Loader2 size={15} className="animate-spin" /> Running…</>
              : <><Rocket size={15} /> Run Pipeline</>
            }
          </button>
        </div>

        {/* Pipeline Stage Visualizer — animated node graph */}
        <div>
          <div className="text-label mb-4">Pipeline Stages</div>
          <div className="flex items-start" style={{ overflowX: 'auto', paddingBottom: 4 }}>
            {PIPELINE_STAGES.map((stage, i) => (
              <PipelineNode
                key={stage.id}
                label={stage.id}
                status={getNodeStatus(i)}
                index={i}
                icon={<stage.icon size={15} />}
                isLast={i === PIPELINE_STAGES.length - 1}
              />
            ))}
          </div>
        </div>

        {/* System readiness — flat inline */}
        <div className="flex items-center gap-6 flex-wrap">
          {readinessItems.map(item => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: item.ready ? 'var(--green)' : 'var(--amber)' }}
              />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
              <span className="text-xs font-medium" style={{ color: item.ready ? 'var(--green)' : 'var(--amber)' }}>
                {item.value || (item.ready ? 'Ready' : 'Missing')}
              </span>
            </div>
          ))}
        </div>

        <div className="divider" />

        {/* Mission Control stream */}
        <MissionControl runId={runId} onComplete={handleComplete} onLogEntry={handleLogEntry} />

        {/* Upload / Paste */}
        <div className="grid grid-cols-2 gap-8">
          {/* Upload JD */}
          <div>
            <div className="text-label mb-2">Upload JD</div>
            <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
              Drop a PDF, image, or text file for a targeted run.
            </p>
            <div
              id="jd-drop-zone"
              className={`drop-zone p-8 text-center cursor-pointer ${dragOver ? 'drag-over' : ''}`}
              onClick={() => document.getElementById('jd-file-input')?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => {
                e.preventDefault();
                setDragOver(false);
                const f = e.dataTransfer.files[0];
                if (f) handleUploadJD(f);
              }}
            >
              <Upload size={20} className="mx-auto mb-2" style={{ color: dragOver ? 'var(--primary)' : 'var(--text-muted)' }} />
              <p className="text-sm font-medium" style={{ color: dragOver ? 'var(--primary)' : 'var(--text-secondary)' }}>
                Click or drag a file
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-faint)' }}>PDF, PNG, JPG, TXT</p>
            </div>
            <input
              id="jd-file-input"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              className="hidden"
              onChange={e => e.target.files?.[0] && handleUploadJD(e.target.files[0])}
            />
          </div>

          {/* Paste JD */}
          <div>
            <div className="text-label mb-2">Paste JD</div>
            <textarea
              id="jd-paste-textarea"
              value={jdText}
              onChange={e => setJdText(e.target.value)}
              rows={5}
              placeholder="Paste the full job description..."
              className="input"
              style={{ minHeight: 120, resize: 'none' }}
            />
            <button
              id="paste-jd-btn"
              onClick={handlePasteJD}
              disabled={jdText.trim().length < 30 || running}
              className="btn btn-primary btn-sm w-full mt-2"
            >
              <FileText size={12} /> Run on this JD
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
