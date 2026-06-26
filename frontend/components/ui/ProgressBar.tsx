'use client';

import { motion } from 'framer-motion';

interface ProgressBarProps {
  value: number;
  max?: number;
  color?: string;
  height?: number;
  showLabel?: boolean;
  animated?: boolean;
}

export default function ProgressBar({
  value,
  max = 100,
  color,
  height = 6,
  showLabel = false,
  animated = true,
}: ProgressBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100);

  const getColor = () => {
    if (color) return color;
    if (pct >= 75) return 'var(--green)';
    if (pct >= 50) return 'var(--amber)';
    return 'var(--red)';
  };

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{Math.round(pct)}%</span>
        </div>
      )}
      <div
        className="w-full rounded-full overflow-hidden"
        style={{ height, background: 'var(--surface-3)' }}
      >
        {animated ? (
          <motion.div
            className="h-full rounded-full"
            style={{ background: getColor() }}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          />
        ) : (
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${pct}%`, background: getColor() }}
          />
        )}
      </div>
    </div>
  );
}
