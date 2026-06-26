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
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

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
    { id: 'dashboard', label: 'Dashboard', description: 'Overview & insights', icon: LayoutDashboard, action: () => navigate('/'), category: 'Navigate' },
    { id: 'jobs', label: 'Jobs', description: 'Browse discovered jobs', icon: Briefcase, action: () => navigate('/jobs'), category: 'Navigate' },
    { id: 'pipeline', label: 'Mission Control', description: 'Run the pipeline', icon: Rocket, action: () => navigate('/pipeline'), category: 'Navigate' },
    { id: 'tracker', label: 'Application Tracker', description: 'Track applications', icon: FileText, action: () => navigate('/tracker'), category: 'Navigate' },
    { id: 'recruiters', label: 'Recruiter Workspace', description: 'Discover contacts', icon: Users, action: () => navigate('/recruiters'), category: 'Navigate' },
    { id: 'startups', label: 'Startup Discovery', description: 'Find target companies', icon: Building2, action: () => navigate('/startups'), category: 'Navigate' },
    { id: 'emails', label: 'Email Drafts', description: 'View drafted emails', icon: Mail, action: () => navigate('/emails'), category: 'Navigate' },
    { id: 'history', label: 'Run History', description: 'Past pipeline runs', icon: History, action: () => navigate('/history'), category: 'Navigate' },
    { id: 'analytics', label: 'Analytics', description: 'Performance insights', icon: BarChart3, action: () => navigate('/analytics'), category: 'Navigate' },
    { id: 'profile', label: 'Profile', description: 'Your career profile', icon: User, action: () => navigate('/profile'), category: 'Navigate' },
    { id: 'settings', label: 'Settings', description: 'Configuration & API keys', icon: Settings, action: () => navigate('/settings'), category: 'Navigate' },
    { id: 'run-pipeline', label: 'Run Pipeline', description: 'Start full job discovery', icon: Zap, action: () => navigate('/pipeline'), category: 'Quick Actions' },
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

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

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
            style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)' }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="fixed left-1/2 top-[20%] -translate-x-1/2 z-[101] w-[540px] overflow-hidden"
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border-hover)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: '0 24px 80px rgba(0, 0, 0, 0.6)',
            }}
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <Search size={16} style={{ color: 'var(--text-muted)' }} />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="flex-1 bg-transparent py-3.5 text-sm outline-none"
                style={{ color: 'var(--text)' }}
              />
            </div>

            {/* Results */}
            <div className="max-h-[320px] overflow-y-auto py-2 px-2">
              {Object.entries(grouped).map(([category, items]) => (
                <div key={category}>
                  <div className="text-label px-3 py-2" style={{ fontSize: 10 }}>
                    {category}
                  </div>
                  {items.map((item) => {
                    const globalIdx = filtered.indexOf(item);
                    return (
                      <button
                        key={item.id}
                        onClick={item.action}
                        onMouseEnter={() => setActiveIndex(globalIdx)}
                        className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors"
                        style={{
                          background: activeIndex === globalIdx ? 'var(--surface-2)' : 'transparent',
                        }}
                      >
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                          style={{ background: 'var(--surface-3)' }}
                        >
                          <item.icon size={14} style={{ color: 'var(--text-secondary)' }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                            {item.label}
                          </div>
                          {item.description && (
                            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                              {item.description}
                            </div>
                          )}
                        </div>
                        {activeIndex === globalIdx && (
                          <ArrowRight size={12} style={{ color: 'var(--text-faint)' }} />
                        )}
                      </button>
                    );
                  })}
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>
                  No results for "{query}"
                </div>
              )}
            </div>

            {/* Footer */}
            <div
              className="flex items-center justify-between px-4 py-2 text-[10px]"
              style={{ borderTop: '1px solid var(--border)', color: 'var(--text-faint)' }}
            >
              <div className="flex items-center gap-3">
                <span>↑↓ Navigate</span>
                <span>↵ Select</span>
                <span>Esc Close</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
