'use client';

import { useEffect, useState } from 'react';
import { Settings, CheckCircle2, XCircle, Mail, Key, Database, Cpu } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { Skeleton } from '@/components/ui/Skeleton';
import { getStatus, getConfig } from '@/lib/api';

function StatusPill({ ok }: { ok: boolean }) {
  return (
    <span
      className="badge"
      style={{
        background: ok ? 'var(--green-muted)' : 'var(--red-muted)',
        color: ok ? 'var(--green)' : 'var(--red)',
      }}
    >
      {ok
        ? <><CheckCircle2 size={9} /> Set</>
        : <><XCircle size={9} /> Missing</>
      }
    </span>
  );
}

function SectionHeader({ icon: Icon, title }: { icon: any; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div
        className="w-6 h-6 rounded-md flex items-center justify-center"
        style={{ background: 'var(--surface-2)' }}
      >
        <Icon size={12} style={{ color: 'var(--primary)' }} />
      </div>
      <div className="text-label">{title}</div>
    </div>
  );
}

export default function SettingsPage() {
  const [envStatus, setEnvStatus] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    getStatus().then(setEnvStatus).catch(() => {});
    getConfig().then(setConfig).catch(() => {});
  }, []);

  const configItems = config ? [
    { key: 'AUTO_APPLY',              value: config.auto_apply ? 'true' : 'false' },
    { key: 'DRY_RUN',                 value: config.dry_run ? 'true' : 'false' },
    { key: 'MIN_FIT_SCORE',           value: String(config.min_fit_score) },
    { key: 'MAX_EMAILS_PER_RUN',      value: String(config.max_emails_per_run) },
    { key: 'MAX_APPLICATIONS_PER_DAY',value: String(config.max_per_day) },
    { key: 'SCHEDULER_ENABLED',       value: config.scheduler_enabled ? 'true' : 'false' },
    { key: 'SCHEDULER_CRON',          value: config.scheduler_cron },
  ] : [];

  function valueColor(value: string) {
    if (value === 'true')  return 'var(--green)';
    if (value === 'false') return 'var(--amber)';
    if (/^\d+$/.test(value)) return 'var(--accent)';
    return 'var(--text-secondary)';
  }

  return (
    <Shell>
      <div className="space-y-10">
        {/* Header */}
        <div>
          <h1 className="text-page-title">Settings</h1>
          <p className="text-body mt-0.5">Environment configuration and API key status.</p>
        </div>

        {/* API Keys */}
        <div>
          <SectionHeader icon={Key} title="API Keys" />
          {envStatus ? (
            <div>
              {Object.entries(envStatus.env_keys || {}).map(([key, ok]) => (
                <div
                  key={key}
                  className="flex items-center justify-between py-2.5 transition-all"
                  style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <code className="text-xs" style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    {key}
                  </code>
                  <StatusPill ok={ok as boolean} />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} height={20} />)}</div>
          )}
        </div>

        <div className="divider" />

        {/* Pipeline Config */}
        <div>
          <SectionHeader icon={Cpu} title="Pipeline Config" />
          <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
            Edit <code style={{ color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>.env</code> to change. Restart backend after saving.
          </p>
          <div>
            {configItems.map(({ key, value }) => (
              <div
                key={key}
                className="flex items-center justify-between py-2.5 font-mono text-xs transition-all"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              >
                <span style={{ color: 'var(--text-muted)' }}>{key}</span>
                <span className="font-bold" style={{ color: valueColor(value) }}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="divider" />

        {/* System health — Email + Apollo */}
        <div className="grid grid-cols-2 gap-12">
          <div>
            <SectionHeader icon={Mail} title="Email" />
            <div className="flex items-center gap-2 mb-3">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: envStatus?.email?.configured ? 'var(--green)' : 'var(--amber)' }}
              />
              <span
                className="text-sm font-medium"
                style={{ color: envStatus?.email?.configured ? 'var(--green)' : 'var(--amber)' }}
              >
                {envStatus?.email?.configured ? 'Configured' : 'Needs setup'}
              </span>
            </div>
            <div className="space-y-1.5 text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              <p>Set <code style={{ color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>RESEND_API_KEY</code> for outbound email through Resend.</p>
              <p>Keep <code style={{ color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>FROM_EMAIL</code> set to a verified sender address.</p>
              <p>For Gmail, complete OAuth authentication.</p>
            </div>
          </div>

          <div>
            <SectionHeader icon={Database} title="Apollo.io" />
            <div className="flex items-center gap-2 mb-3">
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: envStatus?.recruiter_discovery?.apollo ? 'var(--green)' : 'var(--text-faint)' }}
              />
              <span
                className="text-sm font-medium"
                style={{ color: envStatus?.recruiter_discovery?.apollo ? 'var(--green)' : 'var(--text-muted)' }}
              >
                {envStatus?.recruiter_discovery?.apollo ? 'Connected' : 'Not enabled'}
              </span>
            </div>
            <div className="space-y-1.5 text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              <p>Set <code style={{ color: 'var(--primary)', fontFamily: 'var(--font-mono)' }}>APOLLO_API_KEY</code> in .env to enable recruiter discovery.</p>
              <p>Restart the backend after saving.</p>
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}
