'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, Mail, Shield, AlertTriangle, Globe, ExternalLink } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { getRecruiters } from '@/lib/api';

export default function RecruitersPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecruiters().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const recruiters = data?.recruiters || [];
  const warnings = data?.warnings || [];
  const apiStatus = data?.api_status || {};

  return (
    <Shell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>Recruiter Center</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Discovered recruiters and HR contacts
          </p>
        </div>

        {/* API Warnings */}
        {warnings.length > 0 && (
          <div className="space-y-2">
            {warnings.map((w: string, i: number) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs"
                style={{ background: 'var(--amber-muted)', color: 'var(--amber)' }}
              >
                <AlertTriangle size={13} />
                {w}
              </motion.div>
            ))}
          </div>
        )}

        {/* API Status */}
        <div className="grid grid-cols-2 gap-4">
          {Object.entries(apiStatus).map(([key, ok]) => (
            <div key={key} className="rounded-xl p-4 card-hover flex items-center justify-between"
                 style={{ background: 'var(--surface)' }}>
              <div className="flex items-center gap-2">
                <Shield size={14} style={{ color: ok ? 'var(--green)' : 'var(--red)' }} />
                <span className="text-sm font-medium capitalize" style={{ color: 'var(--text)' }}>
                  {key} API
                </span>
              </div>
              <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                    style={{
                      background: ok ? 'var(--green-muted)' : 'var(--red-muted)',
                      color: ok ? 'var(--green)' : 'var(--red)',
                    }}>
                {ok ? '✓ Connected' : '✗ Missing'}
              </span>
            </div>
          ))}
        </div>

        {/* Recruiters Table */}
        <div className="rounded-xl overflow-hidden card-hover" style={{ background: 'var(--surface)' }}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Name', 'Role', 'Email', 'Confidence', 'Source', 'LinkedIn'].map(h => (
                  <th key={h} className="text-left text-[11px] uppercase tracking-wider font-semibold px-4 py-3"
                      style={{ color: 'var(--text-muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>Loading...</td></tr>
              ) : recruiters.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
                    <Users size={24} className="mx-auto mb-2 opacity-40" />
                    No recruiters discovered yet. Run the pipeline to discover contacts.
                  </td>
                </tr>
              ) : (
                recruiters.map((r: any, i: number) => (
                  <motion.tr
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="hover:bg-white/[0.02]"
                    style={{ borderBottom: '1px solid rgba(39,39,42,0.5)' }}
                  >
                    <td className="px-4 py-3 font-medium" style={{ color: 'var(--text)' }}>
                      {r.name || '—'}
                    </td>
                    <td className="px-4 py-3" style={{ color: 'var(--text-secondary)' }}>
                      {r.role || '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--accent)' }}>
                      {r.email || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-12 h-1.5 rounded-full" style={{ background: 'var(--border)' }}>
                          <div className="h-full rounded-full" style={{
                            width: `${r.confidence || 0}%`,
                            background: (r.confidence || 0) > 70 ? 'var(--green)' : 'var(--amber)',
                          }} />
                        </div>
                        <span className="text-[11px] font-mono" style={{ color: 'var(--text-muted)' }}>
                          {r.confidence || 0}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] px-2 py-0.5 rounded"
                            style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}>
                        {r.source || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {r.linkedin ? (
                        <a href={r.linkedin} target="_blank" rel="noopener noreferrer"
                           className="text-xs flex items-center gap-1" style={{ color: 'var(--accent)' }}>
                          <ExternalLink size={12} /> View
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
