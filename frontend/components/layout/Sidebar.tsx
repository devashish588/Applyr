'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, Rocket, Briefcase, Mail, History, Settings,
  User, Users, Building2, BarChart3, FileText, Zap, Search,
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    title: 'Workspace',
    items: [
      { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
      { href: '/jobs', icon: Briefcase, label: 'Jobs' },
      { href: '/tracker', icon: FileText, label: 'Applications' },
      { href: '/recruiters', icon: Users, label: 'Recruiters' },
      { href: '/startups', icon: Building2, label: 'Companies' },
    ],
  },
  {
    title: 'Operations',
    items: [
      { href: '/pipeline', icon: Rocket, label: 'Mission Control' },
      { href: '/emails', icon: Mail, label: 'Email' },
      { href: '/analytics', icon: BarChart3, label: 'Analytics' },
      { href: '/history', icon: History, label: 'History' },
    ],
  },
  {
    title: 'Account',
    items: [
      { href: '/profile', icon: User, label: 'Profile' },
      { href: '/settings', icon: Settings, label: 'Settings' },
    ],
  },
];

interface SidebarProps {
  onOpenCommandPalette?: () => void;
}

export default function Sidebar({ onOpenCommandPalette }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className="flex flex-col shrink-0 h-screen"
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--bg-raised)',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Logo */}
      <div className="px-4 pt-4 pb-2">
        <Link href="/" className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded flex items-center justify-center"
            style={{ background: 'var(--primary)', }}
          >
            <Zap size={12} color="#fff" />
          </div>
          <span className="text-sm font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            Applyr
          </span>
        </Link>
      </div>

      {/* Quick Search */}
      <div className="px-3 py-2">
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-colors"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
        >
          <Search size={12} />
          <span className="flex-1 text-left">Search</span>
          <kbd className="text-[10px] font-mono px-1 rounded" style={{ background: 'var(--surface-2)', color: 'var(--text-faint)' }}>⌘K</kbd>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 pt-1 space-y-4 no-scrollbar">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="text-[10px] font-semibold uppercase tracking-widest px-2.5 mb-1"
              style={{ color: 'var(--text-faint)' }}
            >
              {section.title}
            </div>
            <div className="space-y-px">
              {section.items.map((item) => {
                const isActive =
                  item.href === '/'
                    ? pathname === '/'
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="group flex items-center gap-2 px-2.5 py-[6px] rounded-md text-[13px] relative transition-colors"
                    style={{
                      color: isActive ? 'var(--text)' : 'var(--text-muted)',
                      background: isActive ? 'var(--surface)' : 'transparent',
                      fontWeight: isActive ? 500 : 400,
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--text-secondary)';
                        e.currentTarget.style.background = 'var(--surface-hover)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--text-muted)';
                        e.currentTarget.style.background = 'transparent';
                      }
                    }}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="sidebar-indicator"
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-3.5 rounded-r-full"
                        style={{ background: 'var(--primary)' }}
                        transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                      />
                    )}
                    <item.icon size={14} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <span
            className="w-1.5 h-1.5 rounded-full animate-pulse-dot"
            style={{ background: 'var(--green)' }}
          />
          <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Agent online
          </span>
        </div>
      </div>
    </aside>
  );
}
