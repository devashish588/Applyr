'use client';

import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import TopBar from '@/components/layout/TopBar';
import DryRunBanner from '@/components/layout/DryRunBanner';
import CommandPalette from '@/components/layout/CommandPalette';

export default function Shell({ children }: { children: React.ReactNode }) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const openCommandPalette = useCallback(() => setCommandPaletteOpen(true), []);
  const closeCommandPalette = useCallback(() => setCommandPaletteOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarCollapsed(prev => !prev), []);

  // Persist collapse state
  useEffect(() => {
    const stored = localStorage.getItem('applyr-sidebar-collapsed');
    if (stored === 'true') setSidebarCollapsed(true);
  }, []);

  useEffect(() => {
    localStorage.setItem('applyr-sidebar-collapsed', String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === '\\') {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleSidebar]);

  const sidebarWidth = sidebarCollapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)';

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg)' }}>
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
        onOpenCommandPalette={openCommandPalette}
      />
      <div
        className="flex-1 flex flex-col overflow-hidden"
        style={{ transition: 'margin-left var(--duration-slow) var(--ease-out)' }}
      >
        <DryRunBanner />
        <TopBar
          onOpenCommandPalette={openCommandPalette}
          sidebarCollapsed={sidebarCollapsed}
        />
        <main
          className="flex-1 overflow-y-auto"
          style={{ padding: 'var(--space-8) var(--space-10)' }}
        >
          <div style={{ maxWidth: 'var(--content-max)', margin: '0 auto' }}>
            {children}
          </div>
        </main>
      </div>
      <CommandPalette open={commandPaletteOpen} onClose={closeCommandPalette} />
    </div>
  );
}
