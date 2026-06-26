'use client';

import Sidebar from '@/components/layout/Sidebar';
import DryRunBanner from '@/components/layout/DryRunBanner';

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <DryRunBanner />
        <main className="flex-1 overflow-y-auto" style={{ padding: '28px 32px' }}>
          {children}
        </main>
      </div>
    </div>
  );
}
