'use client';

import { motion } from 'framer-motion';
import { Sparkles, Target } from 'lucide-react';

interface Props {
  roles: string[];
}

export default function ProfileGenerationCard({ roles }: Props) {
  if (!roles || roles.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="card p-5"
    >
      <div className="text-label mb-4 flex items-center gap-2">
        <Sparkles size={11} style={{ color: 'var(--primary)' }} />
        Detected Roles
      </div>

      <div className="space-y-2">
        {roles.map((role, i) => (
          <motion.div
            key={role}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 + i * 0.08 }}
            className="flex items-center gap-3 py-2 px-3 rounded-lg"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}
          >
            <div
              className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold"
              style={{
                background: i === 0 ? 'var(--primary-muted)' : 'var(--accent-muted)',
                color: i === 0 ? 'var(--primary)' : 'var(--accent)',
              }}
            >
              {i + 1}
            </div>
            <div className="flex items-center gap-2">
              <Target size={13} style={{ color: 'var(--text-muted)' }} />
              <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                {role}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
