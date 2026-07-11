'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, Rocket, Briefcase, Mail, History, Settings,
  User, Users, Building2, BarChart3, FileText, Zap, Search,
  ChevronLeft, ChevronRight,
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    title: 'Workspace',
    items: [
      { href: '/',          icon: LayoutDashboard, label: 'Dashboard',    shortcut: '⌘1' },
      { href: '/jobs',      icon: Briefcase,       label: 'Jobs',         shortcut: '⌘2' },
      { href: '/tracker',   icon: FileText,        label: 'Applications', shortcut: '⌘3' },
      { href: '/recruiters',icon: Users,           label: 'Recruiters',   shortcut: '⌘4' },
      { href: '/startups',  icon: Building2,       label: 'Companies',    shortcut: '⌘5' },
    ],
  },
  {
    title: 'Operations',
    items: [
      { href: '/pipeline',  icon: Rocket,   label: 'Mission Control', shortcut: '⌘P' },
      { href: '/emails',    icon: Mail,     label: 'Email',           shortcut: '' },
      { href: '/analytics', icon: BarChart3,label: 'Analytics',       shortcut: '' },
      { href: '/history',   icon: History,  label: 'History',         shortcut: '' },
    ],
  },
  {
    title: 'Account',
    items: [
      { href: '/profile',  icon: User,     label: 'Profile',  shortcut: '' },
      { href: '/settings', icon: Settings, label: 'Settings', shortcut: '' },
    ],
  },
];

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onOpenCommandPalette?: () => void;
}

export default function Sidebar({ collapsed = false, onToggleCollapse, onOpenCommandPalette }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className="flex flex-col shrink-0 h-screen relative"
      style={{
        width: collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)',
        background: 'var(--bg-raised)',
        borderRight: '1px solid var(--border)',
        transition: 'width var(--duration-slow) var(--ease-out)',
        overflow: 'hidden',
      }}
    >
      {/* Logo / Workspace */}
      <div
        className="flex items-center px-4 pt-5 pb-3"
        style={{ minHeight: 60, overflow: 'hidden' }}
      >
        <Link href="/" className="flex items-center gap-3 min-w-0">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
            style={{
              background: 'linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%)',
              boxShadow: '0 2px 8px rgba(124, 92, 252, 0.35)',
            }}
          >
            <Zap size={14} color="#fff" fill="#fff" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="overflow-hidden"
              >
                <div className="text-sm font-bold tracking-tight whitespace-nowrap" style={{ color: 'var(--text)' }}>
                  Applyr
                </div>
                <div className="text-[10px] whitespace-nowrap" style={{ color: 'var(--text-faint)', marginTop: -1 }}>
                  Career OS
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Link>
      </div>

      {/* Quick Search */}
      <div className="px-3 pb-4" style={{ overflow: 'hidden' }}>
        <button
          onClick={onOpenCommandPalette}
          title="Search (⌘K)"
          className="w-full flex items-center rounded-lg text-xs transition-all"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
            height: 30,
            padding: collapsed ? '0 8px' : '0 10px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: collapsed ? 0 : 8,
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
          <Search size={12} style={{ flexShrink: 0 }} />
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.18 }}
                className="flex items-center justify-between flex-1 overflow-hidden"
              >
                <span className="whitespace-nowrap">Search</span>
                <kbd
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0"
                  style={{ background: 'var(--surface-2)', color: 'var(--text-faint)' }}
                >
                  ⌘K
                </kbd>
              </motion.div>
            )}
          </AnimatePresence>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 space-y-5 no-scrollbar">
        {NAV_SECTIONS.map(section => (
          <div key={section.title}>
            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="text-[10px] font-semibold uppercase tracking-widest px-2.5 mb-1.5"
                  style={{ color: 'var(--text-faint)' }}
                >
                  {section.title}
                </motion.div>
              )}
            </AnimatePresence>
            <div className="space-y-0.5">
              {section.items.map(item => {
                const isActive =
                  item.href === '/'
                    ? pathname === '/'
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? item.label : undefined}
                    className="nav-item relative"
                    style={{
                      color: isActive ? 'var(--text)' : 'var(--text-muted)',
                      background: isActive ? 'var(--surface)' : 'transparent',
                      fontWeight: isActive ? 500 : 400,
                      justifyContent: collapsed ? 'center' : 'flex-start',
                      padding: collapsed ? '8px' : '8px 10px',
                    }}
                    onMouseEnter={e => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--text-secondary)';
                        e.currentTarget.style.background = 'var(--surface-hover)';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!isActive) {
                        e.currentTarget.style.color = 'var(--text-muted)';
                        e.currentTarget.style.background = 'transparent';
                      }
                    }}
                  >
                    {/* Active indicator */}
                    {isActive && (
                      <motion.div
                        layoutId="sidebar-indicator"
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] rounded-r-full"
                        style={{
                          height: 18,
                          background: 'var(--primary)',
                          boxShadow: '0 0 8px var(--primary-glow)',
                        }}
                        transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                      />
                    )}
                    <item.icon size={16} style={{ flexShrink: 0 }} />
                    <AnimatePresence>
                      {!collapsed && (
                        <motion.span
                          initial={{ opacity: 0, width: 0 }}
                          animate={{ opacity: 1, width: 'auto' }}
                          exit={{ opacity: 0, width: 0 }}
                          transition={{ duration: 0.18 }}
                          className="overflow-hidden whitespace-nowrap flex-1"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div
        className="px-3 py-3 flex items-center"
        style={{
          borderTop: '1px solid var(--border)',
          justifyContent: collapsed ? 'center' : 'space-between',
          gap: 8,
        }}
      >
        {!collapsed && (
          <div className="flex items-center gap-2 min-w-0">
            <span className="status-dot online" />
            <span className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
              Agent online
            </span>
          </div>
        )}

        {/* Collapse toggle */}
        <button
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar (⌘\\)' : 'Collapse sidebar (⌘\\)'}
          className="w-7 h-7 rounded-md flex items-center justify-center transition-all shrink-0"
          style={{ color: 'var(--text-faint)' }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'var(--surface-2)';
            e.currentTarget.style.color = 'var(--text-secondary)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-faint)';
          }}
        >
          {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
        </button>
      </div>
    </aside>
  );
}
