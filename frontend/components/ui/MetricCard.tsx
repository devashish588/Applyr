'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface MetricCardProps {
  label: string;
  value: number;
  icon?: React.ReactNode;
  color?: string;
  delay?: number;
  suffix?: string;
}

function useCountUp(target: number, duration = 800) {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    if (target === 0) { setCurrent(0); return; }
    const steps = 30;
    const increment = target / steps;
    const interval = duration / steps;
    let step = 0;
    const timer = setInterval(() => {
      step++;
      setCurrent(Math.min(Math.round(increment * step), target));
      if (step >= steps) clearInterval(timer);
    }, interval);
    return () => clearInterval(timer);
  }, [target, duration]);
  return current;
}

export default function MetricCard({ label, value, icon, color, delay = 0, suffix = '' }: MetricCardProps) {
  const animatedValue = useCountUp(value, 700);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay, ease: [0.16, 1, 0.3, 1] }}
      className="metric-card"
    >
      {/* Top row */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-label">{label}</span>
        {icon && (
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--surface-2)' }}
          >
            {icon}
          </div>
        )}
      </div>

      {/* Value */}
      <div
        className="text-3xl font-bold tabular-nums tracking-tight"
        style={{ color: color || 'var(--text)', lineHeight: 1 }}
      >
        {animatedValue.toLocaleString()}{suffix}
      </div>

      {/* Bottom accent line */}
      <div
        className="mt-4 h-0.5 rounded-full"
        style={{
          background: color
            ? `linear-gradient(90deg, ${color}40, ${color}10)`
            : 'linear-gradient(90deg, var(--primary-muted), transparent)',
        }}
      />
    </motion.div>
  );
}
