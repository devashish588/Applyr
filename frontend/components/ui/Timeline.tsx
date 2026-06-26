'use client';

import { ReactNode } from 'react';

interface TimelineItem {
  icon: ReactNode;
  title: string;
  description?: string;
  time?: string;
  color?: string;
}

interface TimelineProps {
  items: TimelineItem[];
}

export default function Timeline({ items }: TimelineProps) {
  return (
    <div className="space-y-0">
      {items.map((item, i) => (
        <div key={i} className="flex gap-3 relative">
          {/* Connector line */}
          {i < items.length - 1 && (
            <div
              className="absolute top-8 left-[13px] w-px h-[calc(100%-16px)]"
              style={{ background: 'var(--border)' }}
            />
          )}
          {/* Icon */}
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 z-10"
            style={{
              background: item.color ? `color-mix(in srgb, ${item.color} 14%, transparent)` : 'var(--surface-2)',
            }}
          >
            {item.icon}
          </div>
          {/* Content */}
          <div className="flex-1 min-w-0 pb-5">
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>
                {item.title}
              </div>
              {item.time && (
                <span className="text-[11px] shrink-0 tabular-nums" style={{ color: 'var(--text-faint)' }}>
                  {item.time}
                </span>
              )}
            </div>
            {item.description && (
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {item.description}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
