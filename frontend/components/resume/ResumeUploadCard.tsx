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
    <div className="rounded-xl p-5 card-hover"
         style={{ background: 'var(--surface)' }}>
      <div className="text-xs font-semibold uppercase tracking-wider mb-4"
           style={{ color: 'var(--text-muted)' }}>
        Resume Upload
      </div>

      <AnimatePresence mode="wait">
        {!result ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div
              className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200"
              style={{
                borderColor: dragOver ? 'var(--accent)' : 'var(--border)',
                background: dragOver ? 'var(--accent-muted)' : 'transparent',
              }}
              onClick={() => document.getElementById('resume-input')?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              {uploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 size={32} className="animate-spin" style={{ color: 'var(--accent)' }} />
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Parsing resume...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Upload size={32} style={{ color: 'var(--text-muted)' }} />
                  <div>
                    <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                      Click or drag your resume
                    </p>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                      PDF, DOCX, TXT supported
                    </p>
                  </div>
                </div>
              )}
            </div>
            <input
              id="resume-input"
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
            />
          </motion.div>
        ) : (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-3 p-3 rounded-lg"
                 style={{ background: result.success ? 'var(--green-muted)' : 'var(--red-muted)' }}>
              {result.success ? (
                <CheckCircle2 size={20} style={{ color: 'var(--green)' }} />
              ) : (
                <XCircle size={20} style={{ color: 'var(--red)' }} />
              )}
              <span className="text-sm font-medium"
                    style={{ color: result.success ? 'var(--green)' : 'var(--red)' }}>
                {result.success ? 'Resume Uploaded ✓' : 'Upload Failed'}
              </span>
            </div>

            {result.success && (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--border)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Filename</span>
                  <span className="font-mono text-xs flex items-center gap-1.5" style={{ color: 'var(--text)' }}>
                    <FileText size={12} />
                    {result.filename}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--border)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Size</span>
                  <span style={{ color: 'var(--text)' }}>{formatFileSize(result.size || 0)}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b" style={{ borderColor: 'var(--border)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Uploaded At</span>
                  <span style={{ color: 'var(--text)' }}>{formatTime(result.uploaded_at)}</span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span style={{ color: 'var(--text-muted)' }}>Parse Status</span>
                  <span className="flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded"
                        style={{
                          color: result.parse_status === 'success' ? 'var(--green)' : 'var(--red)',
                          background: result.parse_status === 'success' ? 'var(--green-muted)' : 'var(--red-muted)',
                        }}>
                    {result.parse_status === 'success' ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                    {result.parse_status === 'success' ? 'Success ✓' : 'Failed'}
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={() => setResult(null)}
              className="w-full py-2 rounded-lg text-xs font-medium transition-colors"
              style={{
                background: 'var(--surface-2)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
              }}
            >
              Upload Different Resume
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
