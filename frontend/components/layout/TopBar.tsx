'use client';

import { usePathname } from 'next/navigation';

interface TopBarProps {
  onOpenCommandPalette?: () => void;
}

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/jobs': 'Jobs',
  '/pipeline': 'Mission Control',
  '/tracker': 'Applications',
  '/recruiters': 'Recruiters',
  '/startups': 'Companies',
  '/emails': 'Email',
  '/history': 'History',
  '/analytics': 'Analytics',
  '/profile': 'Profile',
  '/settings': 'Settings',
};

export default function TopBar({ onOpenCommandPalette }: TopBarProps) {
  const pathname = usePathname();
  const pageTitle = ROUTE_TITLES[pathname] || 'Applyr';

  return (
    <header
      className="glass sticky top-0 z-30 flex items-center justify-between px-7"
      style={{
        height: 'var(--topbar-height)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div className="flex items-center gap-1.5 text-xs">
        <span style={{ color: 'var(--text-faint)' }}>Applyr</span>
        <span style={{ color: 'var(--text-faint)' }}>/</span>
        <span style={{ color: 'var(--text-secondary)' }}>{pageTitle}</span>
      </div>
    </header>
  );
}
