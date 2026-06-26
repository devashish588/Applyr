'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { uploadResume } from '@/lib/api';
import { formatFileSize, formatTime } from '@/lib/utils';

interface UploadResult {
  success: boolean;
  filename?: string;
  size?: number;
  uploaded_at?: string;
  parse_status?: string;
  parse_error?: string;
  inferred_roles?: string[];
  health?: Record<string, boolean>;
  parsed?: any;
}

interface Props {
  onUploadComplete?: (result: UploadResult) => void;
}

export default function ResumeUploadCard({ onUploadComplete }: Props) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const res = await uploadResume(file);
      setResult(res);
      onUploadComplete?.(res);
    } catch (e: any) {
      setResult({ success: false, parse_error: e.message });
    } finally {
      setUploading(false);
    }
  }, [onUploadComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

  return (
    <div className="card p-5">
      <div className="text-label mb-4">Resume Upload</div>

      <AnimatePresence mode="wait">
        {!result ? (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div
              className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all"
              style={{
                borderColor: dragOver ? 'var(--primary)' : 'var(--border)',
                background: dragOver ? 'var(--primary-subtle)' : 'transparent',
                borderRadius: 'var(--radius-lg)',
              }}
              onClick={() => document.getElementById('resume-input')?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onMouseEnter={e => {
                if (!dragOver) {
                  e.currentTarget.style.borderColor = 'var(--border-hover)';
                  e.currentTarget.style.background = 'var(--surface-hover)';
                }
              }}
              onMouseLeave={e => {
                if (!dragOver) {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              {uploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 size={28} className="animate-spin" style={{ color: 'var(--primary)' }} />
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Parsing resume...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Upload size={28} style={{ color: 'var(--text-muted)' }} />
                  <div>
                    <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>Click or drag your resume</p>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-faint)' }}>PDF, DOCX, TXT supported</p>
                  </div>
                </div>
              )}
            </div>
            <input
              id="resume-input"
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              className="hidden"
              onChange={e => e.target.files?.[0] && handleUpload(e.target.files[0])}
            />
          </motion.div>
        ) : (
          <motion.div key="result" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
            <div
              className="flex items-center gap-3 p-3 rounded-lg"
              style={{ background: result.success ? 'var(--green-subtle)' : 'var(--red-subtle)' }}
            >
              {result.success
                ? <CheckCircle2 size={18} style={{ color: 'var(--green)' }} />
                : <XCircle size={18} style={{ color: 'var(--red)' }} />
              }
              <span className="text-sm font-medium" style={{ color: result.success ? 'var(--green)' : 'var(--red)' }}>
                {result.success ? 'Resume Uploaded' : 'Upload Failed'}
              </span>
            </div>

            {result.success && (
              <div className="space-y-1.5 text-sm">
                {[
                  { label: 'File', value: result.filename, mono: true, icon: <FileText size={11} /> },
                  { label: 'Size', value: formatFileSize(result.size || 0) },
                  { label: 'Parsed', value: result.parse_status === 'success' ? 'Success' : 'Failed' },
                ].map((row, i) => (
                  <div key={i} className="flex justify-between py-1.5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{row.label}</span>
                    <span className={`text-xs font-medium flex items-center gap-1 ${row.mono ? 'font-mono' : ''}`} style={{ color: 'var(--text)' }}>
                      {row.icon}{row.value}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <button onClick={() => setResult(null)} className="btn btn-secondary btn-sm w-full">
              Upload Different Resume
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
