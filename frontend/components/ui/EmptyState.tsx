'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  primaryAction?: { label: string; onClick: () => void };
  secondaryAction?: { label: string; onClick: () => void };
}

export default function EmptyState({
  icon,
  title,
  description,
  primaryAction,
  secondaryAction,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col items-center justify-center py-16 px-8 text-center"
    >
      {/* Icon with ambient glow ring */}
      <div className="relative mb-6">
        {/* Outer glow */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: 'radial-gradient(circle, rgba(124, 92, 252, 0.1) 0%, transparent 70%)',
            transform: 'scale(2)',
          }}
        />
        {/* Inner glow ring */}
        <div
          className="absolute inset-0 rounded-2xl"
          style={{
            boxShadow: '0 0 0 1px rgba(124, 92, 252, 0.12), 0 0 24px rgba(124, 92, 252, 0.08)',
          }}
        />
        <motion.div
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className="relative w-16 h-16 rounded-2xl flex items-center justify-center"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
        >
          {icon}
        </motion.div>
      </div>

      <h3 className="text-section-title mb-2">{title}</h3>
      <p className="text-body max-w-sm mb-6 leading-relaxed">{description}</p>

      <div className="flex items-center gap-3">
        {primaryAction && (
          <button
            id={`empty-state-primary-${title.replace(/\s+/g, '-').toLowerCase()}`}
            onClick={primaryAction.onClick}
            className="btn btn-primary"
          >
            {primaryAction.label}
          </button>
        )}
        {secondaryAction && (
          <button
            id={`empty-state-secondary-${title.replace(/\s+/g, '-').toLowerCase()}`}
            onClick={secondaryAction.onClick}
            className="btn btn-secondary"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>
    </motion.div>
  );
}
