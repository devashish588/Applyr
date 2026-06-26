'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Rocket,
  Briefcase,
  Mail,
  History,
  Settings,
  User,
  Users,
  Zap,
  Building2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/pipeline', icon: Rocket, label: 'Pipeline' },
  { href: '/jobs', icon: Briefcase, label: 'Jobs' },
  { href: '/startups', icon: Building2, label: 'Startups' },
  { href: '/emails', icon: Mail, label: 'Drafts' },
  { href: '/recruiters', icon: Users, label: 'Recruiters' },
  { href: '/history', icon: History, label: 'History' },
  { href: '/profile', icon: User, label: 'Profile' },
  { href: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] h-screen flex-shrink-0 flex flex-col border-r"
           style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}>
      {/* Logo */}
      <div className="px-5 py-5 pb-6">
        <Link href="/" className="flex items-center gap-2 no-underline">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: 'var(--accent-muted)' }}>
            <Zap size={16} style={{ color: 'var(--accent)' }} />
          </div>
          <span className="text-lg font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            App<span style={{ color: 'var(--accent)' }}>lyr</span>
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === '/'
            ? pathname === '/'
            : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium no-underline transition-all duration-150 relative',
              )}
              style={{
                color: isActive ? 'var(--text)' : 'var(--text-muted)',
                background: isActive ? 'var(--accent-muted)' : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.color = 'var(--text-secondary)';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
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
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full"
                  style={{ background: 'var(--accent)' }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
              <item.icon size={16} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: 'var(--green)' }} />
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Agent online</span>
        </div>
      </div>
    </aside>
  );
}
