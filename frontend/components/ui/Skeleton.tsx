'use client';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
  className?: string;
}

export function Skeleton({ width, height = 16, rounded = 'md', className = '' }: SkeletonProps) {
  const radiusMap = {
    sm: 'var(--radius-sm)',
    md: 'var(--radius)',
    lg: 'var(--radius-lg)',
    full: 'var(--radius-full)',
  };

  return (
    <div
      className={`shimmer ${className}`}
      style={{
        width: width || '100%',
        height,
        borderRadius: radiusMap[rounded],
      }}
    />
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton width={40} height={40} rounded="lg" />
        <div className="flex-1 space-y-2">
          <Skeleton height={14} width="60%" />
          <Skeleton height={10} width="40%" />
        </div>
      </div>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={10} width={`${90 - i * 15}%`} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} height={10} width={`${100 / cols - 4}%`} />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 py-3 flex gap-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} height={12} width={`${100 / cols - 4}%`} />
          ))}
        </div>
      ))}
    </div>
  );
}
