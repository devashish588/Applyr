'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Shield, ShieldCheck } from 'lucide-react';
import { getConfig } from '@/lib/api';

export default function DryRunBanner() {
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    getConfig().then(setConfig).catch(() => {});
  }, []);

  if (!config) return null;

  const isDryRun = config.dry_run;
  const isAutoApply = config.auto_apply;

  return (
    <AnimatePresence>
      {isDryRun && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div className="flex items-center justify-center gap-3 py-2 px-4 text-xs font-medium"
               style={{
                 background: 'var(--amber-muted)',
                 color: 'var(--amber)',
                 borderBottom: '1px solid rgba(234, 179, 8, 0.15)',
               }}>
            <AlertTriangle size={14} />
            <span>
              <strong>DRY RUN MODE</strong> — Applications will NOT be submitted. Emails will NOT be sent.
            </span>
          </div>
        </motion.div>
      )}
      {!isDryRun && !isAutoApply && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div className="flex items-center justify-center gap-3 py-2 px-4 text-xs font-medium"
               style={{
                 background: 'var(--accent-muted)',
                 color: 'var(--accent)',
                 borderBottom: '1px solid rgba(59, 130, 246, 0.15)',
               }}>
            <Shield size={14} />
            <span>
              <strong>APPROVAL MODE</strong> — Human approval required before sending.
            </span>
          </div>
        </motion.div>
      )}
      {!isDryRun && isAutoApply && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          className="overflow-hidden"
        >
          <div className="flex items-center justify-center gap-3 py-2 px-4 text-xs font-medium"
               style={{
                 background: 'var(--green-muted)',
                 color: 'var(--green)',
                 borderBottom: '1px solid rgba(34, 197, 94, 0.15)',
               }}>
            <ShieldCheck size={14} />
            <span>
              <strong>LIVE MODE</strong> — Applications will be submitted automatically.
            </span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
