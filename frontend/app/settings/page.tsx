'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Key, Sliders, Mail, ShieldCheck, CircleAlert, Sparkles } from 'lucide-react';
import Shell from '@/components/layout/Shell';
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

  const emailHealthy = Boolean(envStatus?.email?.configured);
  const apolloReady = Boolean(envStatus?.recruiter_discovery?.apollo);
  const emailSteps = [
    'Add RESEND_API_KEY to .env if you want outbound email through Resend.',
    'Keep FROM_EMAIL set to the verified sender address for the Resend account.',
    'If you prefer Gmail, finish the Gmail OAuth connection from the app Settings page.',
    'Reload the dashboard after saving .env so the backend picks up the new variables.',
  ];

  return (
    <Shell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>Settings</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Environment configuration and API key status
          </p>
        </div>

        <div className="grid grid-cols-2 gap-5">
          {/* API Keys */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl p-5 card-hover"
            style={{ background: 'var(--surface)' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Key size={12} style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>
                API Keys
              </span>
            </div>

            {envStatus ? (
              <div className="space-y-2">
                {Object.entries(envStatus.env_keys || {}).map(([key, ok]) => (
                  <div key={key} className="flex items-center justify-between py-2 border-b"
                       style={{ borderColor: 'var(--border)' }}>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{key}</span>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded"
                          style={{
                            background: ok ? 'var(--green-muted)' : 'var(--red-muted)',
                            color: ok ? 'var(--green)' : 'var(--red)',
                          }}>
                      {ok ? '✓ Set' : '✗ Missing'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="shimmer h-32 rounded-lg" />
            )}
          </motion.div>

          {/* Pipeline Config */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="rounded-xl p-5 card-hover"
            style={{ background: 'var(--surface)' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Sliders size={12} style={{ color: 'var(--purple)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>
                Pipeline Config
              </span>
            </div>

            <div className="text-xs mb-3" style={{ color: 'var(--text-muted)', lineHeight: 1.8 }}>
              Edit <code className="px-1.5 py-0.5 rounded" style={{ background: 'var(--surface-2)', color: 'var(--accent)' }}>.env</code> to change these values.
            </div>

            <div className="space-y-2">
              {configItems.map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-1.5 font-mono text-xs">
                  <span style={{ color: 'var(--text-muted)' }}>{key}</span>
                  <span className="px-2 py-0.5 rounded"
                        style={{
                          color: value === 'true' ? 'var(--green)' : value === 'false' ? 'var(--amber)' : 'var(--accent)',
                          background: 'var(--surface-2)',
                        }}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <div className="grid grid-cols-2 gap-5">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-2xl p-5 card-hover"
            style={{ background: 'var(--surface)' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Mail size={12} style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Email Health
              </span>
              <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full" style={{ background: emailHealthy ? 'var(--green-muted)' : 'var(--amber-muted)', color: emailHealthy ? 'var(--green)' : 'var(--amber)' }}>
                {emailHealthy ? 'Healthy' : 'Missing Configuration'}
              </span>
            </div>

            <div className="space-y-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
              {emailSteps.map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <ShieldCheck size={14} style={{ color: emailHealthy ? 'var(--green)' : 'var(--amber)', marginTop: 2 }} />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="rounded-2xl p-5 card-hover"
            style={{ background: 'var(--surface)' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={12} style={{ color: 'var(--purple)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Apollo.io Status
              </span>
              <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full" style={{ background: apolloReady ? 'var(--green-muted)' : 'var(--surface-2)', color: apolloReady ? 'var(--green)' : 'var(--text-muted)' }}>
                {apolloReady ? 'Connected' : 'Not Enabled'}
              </span>
            </div>

            <div className="text-sm leading-6" style={{ color: 'var(--text-secondary)' }}>
              Apollo is used for recruiter discovery. Set <code className="px-1.5 py-0.5 rounded" style={{ background: 'var(--surface-2)', color: 'var(--accent)' }}>APOLLO_API_KEY</code> in .env, then rerun the app.
            </div>
            <div className="mt-4 rounded-xl p-4 border" style={{ background: 'rgba(59,130,246,0.06)', borderColor: 'rgba(59,130,246,0.16)' }}>
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: 'var(--accent)' }}>
                <CircleAlert size={14} />
                Email health fix order
              </div>
              <ol className="mt-3 space-y-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <li>1. Set `RESEND_API_KEY` and `FROM_EMAIL` in .env for the cleanest path.</li>
                <li>2. If using Gmail, finish OAuth authentication and store the token.</li>
                <li>3. Restart the backend so the new env values are loaded.</li>
              </ol>
            </div>
          </motion.div>
        </div>
      </div>
    </Shell>
  );
}
