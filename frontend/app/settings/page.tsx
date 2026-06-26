'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Key, Sliders, Mail, ShieldCheck, CircleAlert } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { Skeleton } from '@/components/ui/Skeleton';
import { getStatus, getConfig } from '@/lib/api';

export default function SettingsPage() {
  const [envStatus, setEnvStatus] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    getStatus().then(setEnvStatus).catch(() => {});
    getConfig().then(setConfig).catch(() => {});
  }, []);

  const configItems = config ? [
    ['AUTO_APPLY', config.auto_apply ? 'true' : 'false'],
    ['DRY_RUN', config.dry_run ? 'true' : 'false'],
    ['MIN_FIT_SCORE', String(config.min_fit_score)],
    ['MAX_EMAILS_PER_RUN', String(config.max_emails_per_run)],
    ['MAX_APPLICATIONS_PER_DAY', String(config.max_per_day)],
    ['SCHEDULER_ENABLED', config.scheduler_enabled ? 'true' : 'false'],
    ['SCHEDULER_CRON', config.scheduler_cron],
  ] : [];

  return (
    <Shell>
      <div className="space-y-10">
        <div>
          <h1 className="text-page-title">Settings</h1>
          <p className="text-body mt-0.5">Environment configuration and API key status.</p>
        </div>

        {/* API Keys — flat table, no card */}
        <div>
          <div className="text-label mb-4">API Keys</div>
          {envStatus ? (
            <div className="space-y-0">
              {Object.entries(envStatus.env_keys || {}).map(([key, ok]) => (
                <div key={key} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{key}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: ok ? 'var(--green)' : 'var(--red)' }} />
                    <span className="text-xs" style={{ color: ok ? 'var(--green)' : 'var(--red)' }}>
                      {ok ? 'Set' : 'Missing'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} height={20} />)}</div>
          )}
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Pipeline Config — flat table */}
        <div>
          <div className="text-label mb-2">Pipeline Config</div>
          <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
            Edit <code className="font-mono" style={{ color: 'var(--primary)' }}>.env</code> to change. Restart backend after saving.
          </p>
          <div className="space-y-0">
            {configItems.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between py-2 font-mono text-xs" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>{key}</span>
                <span style={{ color: value === 'true' ? 'var(--green)' : value === 'false' ? 'var(--amber)' : 'var(--text-secondary)' }}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* System Health — flat inline */}
        <div className="grid grid-cols-2 gap-12">
          <div>
            <div className="text-label mb-4">Email</div>
            <div className="flex items-center gap-1.5 mb-3">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: envStatus?.email?.configured ? 'var(--green)' : 'var(--amber)' }} />
              <span className="text-sm" style={{ color: envStatus?.email?.configured ? 'var(--green)' : 'var(--amber)' }}>
                {envStatus?.email?.configured ? 'Configured' : 'Needs setup'}
              </span>
            </div>
            <div className="space-y-2 text-xs" style={{ color: 'var(--text-muted)' }}>
              <p>Set RESEND_API_KEY for outbound email through Resend.</p>
              <p>Keep FROM_EMAIL set to a verified sender address.</p>
              <p>For Gmail, complete OAuth authentication.</p>
            </div>
          </div>

          <div>
            <div className="text-label mb-4">Apollo.io</div>
            <div className="flex items-center gap-1.5 mb-3">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: envStatus?.recruiter_discovery?.apollo ? 'var(--green)' : 'var(--text-faint)' }} />
              <span className="text-sm" style={{ color: envStatus?.recruiter_discovery?.apollo ? 'var(--green)' : 'var(--text-muted)' }}>
                {envStatus?.recruiter_discovery?.apollo ? 'Connected' : 'Not enabled'}
              </span>
            </div>
            <div className="space-y-2 text-xs" style={{ color: 'var(--text-muted)' }}>
              <p>Set <code className="font-mono" style={{ color: 'var(--primary)' }}>APOLLO_API_KEY</code> in .env to enable recruiter discovery.</p>
              <p>Restart the backend after saving.</p>
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}
