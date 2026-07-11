'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, LayoutDashboard, Briefcase, Rocket, Users, Building2,
  Mail, History, BarChart3, User, Settings, FileText, Zap, ArrowRight,
} from 'lucide-react';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: any;
  action: () => void;
  category: string;
  iconColor?: string;
  shortcut?: string;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

const CATEGORY_ORDER = ['Quick Actions', 'Navigate'];

export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  const navigate = useCallback((path: string) => {
    router.push(path);
    onClose();
  }, [router, onClose]);

  const commands: CommandItem[] = [
    {
      id: 'run-pipeline', label: 'Run Pipeline', description: 'Start full job discovery now',
      icon: Zap, action: () => navigate('/pipeline'), category: 'Quick Actions',
      iconColor: 'var(--primary)', shortcut: '⌘P',
    },
    {
      id: 'dashboard', label: 'Dashboard', description: 'Overview & AI insights',
      icon: LayoutDashboard, action: () => navigate('/'), category: 'Navigate',
      iconColor: 'var(--text-secondary)',
    },
    {
      id: 'jobs', label: 'Jobs', description: 'Browse discovered jobs',
      icon: Briefcase, action: () => navigate('/jobs'), category: 'Navigate',
      iconColor: 'var(--accent)',
    },
    {
      id: 'pipeline', label: 'Mission Control', description: 'Run the pipeline, upload JD',
      icon: Rocket, action: () => navigate('/pipeline'), category: 'Navigate',
      iconColor: 'var(--primary)',
    },
    {
      id: 'tracker', label: 'Applications', description: 'Kanban application tracker',
      icon: FileText, action: () => navigate('/tracker'), category: 'Navigate',
      iconColor: 'var(--cyan)',
    },
    {
      id: 'recruiters', label: 'Recruiters', description: 'Discover HR contacts',
      icon: Users, action: () => navigate('/recruiters'), category: 'Navigate',
      iconColor: 'var(--green)',
    },
    {
      id: 'startups', label: 'Companies', description: 'Find target companies',
      icon: Building2, action: () => navigate('/startups'), category: 'Navigate',
      iconColor: 'var(--amber)',
    },
    {
      id: 'emails', label: 'Email Drafts', description: 'View drafted & sent emails',
      icon: Mail, action: () => navigate('/emails'), category: 'Navigate',
      iconColor: 'var(--accent)',
    },
    {
      id: 'history', label: 'Run History', description: 'Past pipeline runs',
      icon: History, action: () => navigate('/history'), category: 'Navigate',
      iconColor: 'var(--text-secondary)',
    },
    {
      id: 'analytics', label: 'Analytics', description: 'Performance insights & charts',
      icon: BarChart3, action: () => navigate('/analytics'), category: 'Navigate',
      iconColor: 'var(--green)',
    },
    {
      id: 'profile', label: 'Profile', description: 'Your career profile',
      icon: User, action: () => navigate('/profile'), category: 'Navigate',
      iconColor: 'var(--text-secondary)',
    },
    {
      id: 'settings', label: 'Settings', description: 'Configuration & API keys',
      icon: Settings, action: () => navigate('/settings'), category: 'Navigate',
      iconColor: 'var(--text-secondary)',
    },
  ];

  const filtered = query.trim()
    ? commands.filter(c =>
        c.label.toLowerCase().includes(query.toLowerCase()) ||
        (c.description || '').toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  const grouped = filtered.reduce((acc, item) => {
    if (!acc[item.category]) acc[item.category] = [];
    acc[item.category].push(item);
    return acc;
  }, {} as Record<string, CommandItem[]>);

  const orderedCategories = CATEGORY_ORDER.filter(c => grouped[c]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => { setActiveIndex(0); }, [query]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex(prev => Math.min(prev + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' && filtered[activeIndex]) {
        e.preventDefault();
        filtered[activeIndex].action();
      } else if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, filtered, activeIndex, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-[100]"
            style={{ background: 'rgba(0, 0, 0, 0.65)', backdropFilter: 'blur(6px)' }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -8 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="fixed left-1/2 top-[18%] -translate-x-1/2 z-[101] w-[560px] overflow-hidden"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-hover)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: '0 32px 80px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(124,92,252,0.08)',
            }}
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <Search size={15} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="flex-1 bg-transparent py-4 text-sm outline-none"
                style={{ color: 'var(--text)' }}
              />
              <kbd
                className="text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0"
                style={{ background: 'var(--surface-2)', color: 'var(--text-faint)', border: '1px solid var(--border)' }}
              >
                Esc
              </kbd>
            </div>

            {/* Results */}
            <div className="max-h-[360px] overflow-y-auto py-2 px-2">
              {orderedCategories.map(category => (
                <div key={category}>
                  <div
                    className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-faint)' }}
                  >
                    {category}
                  </div>
                  {grouped[category].map(item => {
                    const globalIdx = filtered.indexOf(item);
                    const isActive = activeIndex === globalIdx;
                    return (
                      <button
                        key={item.id}
                        id={`cmd-${item.id}`}
                        onClick={item.action}
                        onMouseEnter={() => setActiveIndex(globalIdx)}
                        className="cmd-item"
                        style={{
                          background: isActive ? 'var(--surface-2)' : 'transparent',
                        }}
                      >
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                          style={{
                            background: isActive ? 'var(--surface-3)' : 'var(--surface-2)',
                            transition: 'background var(--duration)',
                          }}
                        >
                          <item.icon size={15} style={{ color: isActive ? (item.iconColor || 'var(--text-secondary)') : 'var(--text-muted)' }} />
                        </div>
                        <div className="flex-1 min-w-0 text-left">
                          <div className="text-sm font-medium" style={{ color: isActive ? 'var(--text)' : 'var(--text-secondary)' }}>
                            {item.label}
                          </div>
                          {item.description && (
                            <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-faint)' }}>
                              {item.description}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {item.shortcut && (
                            <kbd
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                              style={{
                                background: 'var(--surface-3)',
                                color: 'var(--text-faint)',
                                border: '1px solid var(--border)',
                              }}
                            >
                              {item.shortcut}
                            </kbd>
                          )}
                          {isActive && (
                            <ArrowRight size={12} style={{ color: 'var(--text-faint)' }} />
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              ))}

              {filtered.length === 0 && (
                <div className="text-center py-10 text-sm" style={{ color: 'var(--text-muted)' }}>
                  No results for &quot;{query}&quot;
                </div>
              )}
            </div>

            {/* Footer */}
            <div
              className="flex items-center justify-between px-4 py-2 text-[10px]"
              style={{ borderTop: '1px solid var(--border)', color: 'var(--text-faint)' }}
            >
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <kbd className="font-mono px-1 py-0.5 rounded text-[10px]" style={{ border: '1px solid var(--border)', background: 'var(--surface-2)' }}>↑↓</kbd>
                  Navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="font-mono px-1 py-0.5 rounded text-[10px]" style={{ border: '1px solid var(--border)', background: 'var(--surface-2)' }}>↵</kbd>
                  Open
                </span>
              </div>
              <span style={{ color: 'var(--text-faint)' }}>{filtered.length} results</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
