'use client';

import { motion } from 'framer-motion';
import { CheckCircle2, Circle, FileCheck, UserCheck, Database, Search } from 'lucide-react';

interface HealthStatus {
  resume_parsed: boolean;
  profile_generated: boolean;
  embedding_created: boolean;
  ready_for_search: boolean;
}

interface Props {
  health: HealthStatus | null;
}

const STEPS = [
  { key: 'resume_parsed', label: 'Resume Parsed', icon: FileCheck },
  { key: 'profile_generated', label: 'Profile Generated', icon: UserCheck },
  { key: 'embedding_created', label: 'Embedding Created', icon: Database },
  { key: 'ready_for_search', label: 'Ready For Job Search', icon: Search },
];

export default function ResumeHealthCard({ health }: Props) {
  if (!health) return null;

  const allGood = Object.values(health).every(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="card p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="text-label">Resume Health</div>
        {allGood && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, delay: 0.6 }}
            className="badge badge-green"
          >
            All systems go
          </motion.span>
        )}
      </div>

      <div className="space-y-3">
        {STEPS.map((step, i) => {
          const done = health[step.key as keyof HealthStatus];
          return (
            <motion.div
              key={step.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.35 + i * 0.1 }}
              className="flex items-center gap-3"
            >
              {done ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 500, delay: 0.4 + i * 0.1 }}
                >
                  <CheckCircle2 size={16} style={{ color: 'var(--green)' }} />
                </motion.div>
              ) : (
                <Circle size={16} style={{ color: 'var(--text-faint)' }} />
              )}
              <step.icon size={13} style={{ color: done ? 'var(--text-secondary)' : 'var(--text-faint)' }} />
              <span className="text-sm" style={{ color: done ? 'var(--text)' : 'var(--text-muted)' }}>
                {step.label}
              </span>
              {done && (
                <span className="text-[10px] font-medium ml-auto" style={{ color: 'var(--green)' }}>✓</span>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
