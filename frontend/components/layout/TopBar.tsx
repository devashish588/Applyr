'use client';

import { usePathname } from 'next/navigation';
import { Search } from 'lucide-react';

interface TopBarProps {
  onOpenCommandPalette?: () => void;
  sidebarCollapsed?: boolean;
}

const ROUTE_TITLES: Record<string, string> = {
  '/':           'Dashboard',
  '/jobs':       'Jobs',
  '/pipeline':   'Mission Control',
  '/tracker':    'Applications',
  '/recruiters': 'Recruiters',
  '/startups':   'Companies',
  '/emails':     'Email',
  '/history':    'History',
  '/analytics':  'Analytics',
  '/profile':    'Profile',
  '/settings':   'Settings',
};

export default function TopBar({ onOpenCommandPalette }: TopBarProps) {
  const pathname = usePathname();
  const pageTitle = ROUTE_TITLES[pathname] || 'Applyr';

  return (
    <header
      className="glass sticky top-0 z-30 flex items-center justify-between"
      style={{
        height: 'var(--topbar-height)',
        borderBottom: '1px solid var(--border)',
        paddingLeft: 'var(--space-6)',
        paddingRight: 'var(--space-5)',
      }}
    >
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs">
        <span style={{ color: 'var(--text-faint)' }}>Applyr</span>
        <span style={{ color: 'var(--text-faint)' }}>/</span>
        <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{pageTitle}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Live status */}
        <div className="flex items-center gap-1.5">
          <span className="status-dot online" />
          <span className="text-xs hidden sm:block" style={{ color: 'var(--text-muted)' }}>
            Online
          </span>
        </div>

        {/* ⌘K trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-2.5 py-1 rounded-md text-xs transition-all"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--border-hover)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--border)';
            e.currentTarget.style.color = 'var(--text-muted)';
          }}
        >
          <Search size={11} />
          <kbd className="font-mono" style={{ fontSize: 10 }}>⌘K</kbd>
        </button>
      </div>
    </header>
  );
}
