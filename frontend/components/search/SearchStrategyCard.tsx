'use client';

import { motion } from 'framer-motion';
import { Search, MapPin, Hash } from 'lucide-react';

interface Strategy {
  roles: string[];
  locations: string[];
  keywords: string[];
  query?: string;
  source?: string;
}

interface Props {
  strategy: Strategy | null;
}

export default function SearchStrategyCard({ strategy }: Props) {
  if (!strategy) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="rounded-xl p-5 card-hover"
      style={{ background: 'var(--surface)' }}
    >
      <div className="flex items-center gap-2 mb-4">
        <Search size={12} style={{ color: 'var(--accent)' }} />
        <span className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: 'var(--text-muted)' }}>
          Search Strategy
        </span>
        {strategy.source && (
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded"
                style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}>
            {strategy.source}
          </span>
        )}
      </div>

      <div className="space-y-4">
        {/* Roles */}
        <div>
          <div className="text-[10px] uppercase tracking-wider font-semibold mb-2"
               style={{ color: 'var(--text-muted)' }}>
            Roles
          </div>
          <div className="flex flex-wrap gap-1.5">
            {strategy.roles.map((role, i) => (
              <span key={i} className="text-[11px] px-2.5 py-1 rounded-md font-medium"
                    style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>
                {role}
              </span>
            ))}
          </div>
        </div>

        {/* Locations */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <MapPin size={10} style={{ color: 'var(--text-muted)' }} />
            <span className="text-[10px] uppercase tracking-wider font-semibold"
                  style={{ color: 'var(--text-muted)' }}>
              Locations
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {strategy.locations.map((loc, i) => (
              <span key={i} className="text-[11px] px-2.5 py-1 rounded-md font-medium"
                    style={{ background: 'var(--green-muted)', color: 'var(--green)' }}>
                {loc}
              </span>
            ))}
          </div>
        </div>

        {/* Keywords */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Hash size={10} style={{ color: 'var(--text-muted)' }} />
            <span className="text-[10px] uppercase tracking-wider font-semibold"
                  style={{ color: 'var(--text-muted)' }}>
              Keywords
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {strategy.keywords.map((kw, i) => (
              <span key={i} className="text-[11px] px-2 py-0.5 rounded-md"
                    style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
