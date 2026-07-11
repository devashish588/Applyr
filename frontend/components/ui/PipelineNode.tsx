'use client';

import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, XCircle, Circle } from 'lucide-react';

export type NodeStatus = 'idle' | 'active' | 'complete' | 'error';

interface PipelineNodeProps {
  label: string;
  status: NodeStatus;
  index: number;
  icon?: React.ReactNode;
  isLast?: boolean;
}

const STATUS_CONFIG: Record<NodeStatus, { borderColor: string; bg: string; textColor: string; iconColor: string }> = {
  idle:     { borderColor: 'var(--border)',   bg: 'var(--surface-2)',    textColor: 'var(--text-faint)',     iconColor: 'var(--text-faint)' },
  active:   { borderColor: 'var(--primary)',  bg: 'var(--primary-muted)',textColor: 'var(--primary)',        iconColor: 'var(--primary)' },
  complete: { borderColor: 'var(--green)',    bg: 'var(--green-muted)',  textColor: 'var(--green)',          iconColor: 'var(--green)' },
  error:    { borderColor: 'var(--red)',      bg: 'var(--red-muted)',    textColor: 'var(--red)',            iconColor: 'var(--red)' },
};

function StatusIcon({ status, icon }: { status: NodeStatus; icon?: React.ReactNode }) {
  if (status === 'complete') return <CheckCircle2 size={16} />;
  if (status === 'error')    return <XCircle size={16} />;
  if (status === 'active')   return <Loader2 size={16} className="animate-spin" />;
  if (icon) return <span>{icon}</span>;
  return <Circle size={14} />;
}

export default function PipelineNode({ label, status, index, icon, isLast }: PipelineNodeProps) {
  const cfg = STATUS_CONFIG[status];

  return (
    <div className="flex items-center flex-1 min-w-0">
      {/* Node */}
      <motion.div
        className="flex flex-col items-center gap-2 flex-shrink-0"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: index * 0.05, duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      >
        <div
          className="pipeline-node-circle"
          style={{
            background: cfg.bg,
            borderColor: cfg.borderColor,
            color: cfg.iconColor,
            boxShadow: status === 'active'
              ? `0 0 0 4px ${cfg.bg}, 0 0 20px rgba(124,92,252,0.25)`
              : status === 'complete'
              ? `0 0 0 3px var(--green-subtle)`
              : 'none',
          }}
        >
          <StatusIcon status={status} icon={icon} />
        </div>
        <span
          className="text-[10px] font-medium text-center leading-tight max-w-[60px]"
          style={{ color: cfg.textColor }}
        >
          {label}
        </span>
      </motion.div>

      {/* Connector line */}
      {!isLast && (
        <div
          className="pipeline-connector mx-2"
          style={{ flexShrink: 1 }}
        >
          {status === 'complete' && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: 'linear-gradient(90deg, var(--green), var(--primary))',
                borderRadius: 1,
                animation: 'line-fill 0.4s var(--ease-out) forwards',
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
