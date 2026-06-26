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

  const bannerConfig = isDryRun
    ? {
        icon: AlertTriangle,
        label: 'Sandbox',
        message: 'Applications will not be submitted. Emails will not be sent.',
        bg: 'var(--amber-subtle)',
        color: 'var(--amber)',
        border: 'rgba(251, 191, 36, 0.1)',
      }
    : !isAutoApply
    ? {
        icon: Shield,
        label: 'Review',
        message: 'Human approval required before sending.',
        bg: 'var(--primary-subtle)',
        color: 'var(--primary)',
        border: 'rgba(124, 92, 252, 0.1)',
      }
    : {
        icon: ShieldCheck,
        label: 'Live',
        message: 'Applications will be submitted automatically.',
        bg: 'var(--green-subtle)',
        color: 'var(--green)',
        border: 'rgba(52, 211, 153, 0.1)',
      };

  const Icon = bannerConfig.icon;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        exit={{ height: 0, opacity: 0 }}
        className="overflow-hidden"
      >
        <div
          className="flex items-center justify-center gap-2.5 py-1.5 px-4 text-xs"
          style={{
            background: bannerConfig.bg,
            borderBottom: `1px solid ${bannerConfig.border}`,
            color: bannerConfig.color,
          }}
        >
          <Icon size={12} />
          <span className="font-semibold">{bannerConfig.label}</span>
          <span style={{ color: 'var(--text-muted)' }}>—</span>
          <span style={{ opacity: 0.85 }}>{bannerConfig.message}</span>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
