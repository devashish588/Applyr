'use client';

import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, AlertTriangle, ArrowRight } from 'lucide-react';
import { getScoreColor, getScoreLabel } from '@/lib/utils';

interface MatchData {
  fit_score: number;
  matched_skills?: string[];
  missing_skills?: string[];
  explanation?: string;
  recommendation?: string;
}

interface Props {
  match: MatchData | null;
}

export default function MatchScoreCard({ match }: Props) {
  if (!match) return null;

  const score = match.fit_score || 0;
  const color = getScoreColor(score);
  const label = getScoreLabel(score);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl p-5 card-hover"
      style={{ background: 'var(--surface)' }}
    >
      <div className="text-xs font-semibold uppercase tracking-wider mb-4"
           style={{ color: 'var(--text-muted)' }}>
        Match Breakdown
      </div>

      {/* Score display */}
      <div className="flex items-center gap-4 mb-4">
        <div className="relative w-16 h-16">
          <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="none" stroke="var(--border)" strokeWidth="4" />
            <motion.circle
              cx="32" cy="32" r="28" fill="none"
              stroke={color}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 28}`}
              initial={{ strokeDashoffset: 2 * Math.PI * 28 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 28 * (1 - score / 100) }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-bold" style={{ color }}>{score}</span>
          </div>
        </div>
        <div>
          <div className="text-sm font-semibold" style={{ color }}>{label}</div>
          {match.recommendation && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded mt-1"
                  style={{
                    background: match.recommendation === 'Apply' ? 'var(--green-muted)' :
                               match.recommendation === 'Consider' ? 'var(--amber-muted)' : 'var(--red-muted)',
                    color: match.recommendation === 'Apply' ? 'var(--green)' :
                          match.recommendation === 'Consider' ? 'var(--amber)' : 'var(--red)',
                  }}>
              <ArrowRight size={10} />
              {match.recommendation}
            </span>
          )}
        </div>
      </div>

      {/* Matched skills */}
      {match.matched_skills && match.matched_skills.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] uppercase tracking-wider font-semibold mb-2"
               style={{ color: 'var(--text-muted)' }}>
            Matched Skills
          </div>
          <div className="space-y-1">
            {match.matched_skills.map((skill, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <CheckCircle2 size={12} style={{ color: 'var(--green)' }} />
                <span style={{ color: 'var(--text)' }}>{skill}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing skills */}
      {match.missing_skills && match.missing_skills.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] uppercase tracking-wider font-semibold mb-2"
               style={{ color: 'var(--text-muted)' }}>
            Missing Skills
          </div>
          <div className="space-y-1">
            {match.missing_skills.map((skill, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <XCircle size={12} style={{ color: 'var(--red)' }} />
                <span style={{ color: 'var(--text-muted)' }}>{skill}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Explanation */}
      {match.explanation && (
        <div className="pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-start gap-2">
            <AlertTriangle size={12} className="shrink-0 mt-0.5" style={{ color: 'var(--amber)' }} />
            <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {match.explanation}
            </p>
          </div>
        </div>
      )}
    </motion.div>
  );
}
