'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Zap, Mail, Search, Rocket, Upload, Sparkles, ArrowRight,
} from 'lucide-react';
import { buildCommandCenter, type CommandCenterChip } from '@/lib/insights';

const ICONS = { zap: Zap, mail: Mail, search: Search, rocket: Rocket, upload: Upload, sparkles: Sparkles };

interface Props {
  analytics?: any;
  jobs?: any[];
  resumeData?: any;
  status?: any;
  followupsDue?: any[];
  recruiters?: any[];
}

function Action({ chip }: { chip: CommandCenterChip }) {
  const Icon = ICONS[chip.icon] ?? Sparkles;
  return (
    <Link
      href={chip.href}
      className="inline-flex items-center gap-1.5 text-sm transition-all group"
      style={{
        color: chip.primary ? 'var(--primary)' : 'var(--text-secondary)',
        padding: '4px 8px',
        borderRadius: 'var(--radius-sm)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.color = chip.primary ? 'var(--primary-hover)' : 'var(--text)';
        e.currentTarget.style.background = chip.primary ? 'var(--primary-subtle)' : 'var(--surface-hover)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.color = chip.primary ? 'var(--primary)' : 'var(--text-secondary)';
        e.currentTarget.style.background = 'transparent';
      }}
    >
      <Icon size={13} />
      {chip.label}
      <ArrowRight size={10} className="opacity-0 group-hover:opacity-100 transition-opacity -ml-0.5" />
    </Link>
  );
}

/**
 * Signature AI intro — pure typography, no container.
 * Greeting + a single rule-based recommendation line, then quiet text actions.
 */
export default function CommandCenter(props: Props) {
  const cc = buildCommandCenter(props);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="flex items-center gap-1.5 mb-3">
        <Sparkles size={12} style={{ color: 'var(--primary)' }} />
        <span className="text-label" style={{ color: 'var(--primary)' }}>Applyr AI</span>
      </div>

      <h1 className="text-display mb-3">{cc.greeting}</h1>

      <p className="max-w-2xl" style={{ color: 'var(--text-secondary)', fontSize: 15, lineHeight: 1.6 }}>
        {cc.recommendation}
      </p>

      {/* Gradient divider */}
      <div
        className="my-5"
        style={{
          height: 1,
          background: 'linear-gradient(90deg, var(--border-hover) 0%, transparent 80%)',
        }}
      />

      <div className="flex flex-wrap items-center gap-1 -ml-2">
        {cc.chips.map(chip => <Action key={chip.label + chip.href} chip={chip} />)}
      </div>
    </motion.div>
  );
}
