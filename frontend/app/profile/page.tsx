'use client';

import { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { CheckSquare, Square, Save, Loader2, Sparkles, MapPin, Mail } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { Skeleton } from '@/components/ui/Skeleton';
import { getProfile, updateProfile, getResumeParsed } from '@/lib/api';

const DEFAULT_ROLES = [
  'Machine Learning Engineer', 'Data Scientist', 'AI Engineer',
  'Data Analyst', 'ML Intern', 'Full Stack Developer',
  'Backend Engineer', 'Software Engineer', 'DevOps Engineer',
  'Frontend Developer',
];

const SKILL_COLORS: Record<string, { bg: string; color: string }> = {
  languages:  { bg: 'var(--accent-muted)',   color: 'var(--accent)' },
  frameworks: { bg: 'var(--primary-muted)',  color: 'var(--primary)' },
  tools:      { bg: 'var(--amber-muted)',    color: 'var(--amber)' },
};

function extractRoleString(item: any): string {
  if (typeof item === 'string') return item;
  if (item && typeof item === 'object' && item.role) return String(item.role);
  return String(item);
}

function GradientAvatar({ name, size = 48 }: { name: string; size?: number }) {
  const initials = (name || '?').split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
  const hue = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div
      className="flex items-center justify-center rounded-2xl text-white font-bold shrink-0"
      style={{
        width: size,
        height: size,
        background: `linear-gradient(135deg, hsl(${hue},65%,55%), hsl(${(hue + 80) % 360},60%,50%))`,
        fontSize: size * 0.38,
        boxShadow: `0 0 0 3px rgba(255,255,255,0.06), 0 4px 16px hsl(${hue},50%,40%,0.25)`,
      }}
    >
      {initials}
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [resumeData, setResumeData] = useState<any>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getProfile().then(r => {
      setProfile(r.profile);
      setSelectedRoles(r.profile?.job_preferences?.target_roles || []);
    }).catch(() => {});
    getResumeParsed().then(r => { if (r.success) setResumeData(r); }).catch(() => {});
  }, []);

  const inferredRoles = useMemo(() => (resumeData?.roles_json || []).map(extractRoleString), [resumeData]);

  const allRoles = useMemo(() => {
    const set = new Set<string>([
      ...inferredRoles,
      ...(profile?.job_preferences?.target_roles || []).map(extractRoleString),
      ...DEFAULT_ROLES,
    ]);
    return Array.from(set);
  }, [inferredRoles, profile]);

  const toggleRole = (role: string) =>
    setSelectedRoles(prev => prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ target_roles: selectedRoles });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
    setSaving(false);
  };

  const personal = profile?.personal || {};
  const skills   = profile?.skills || {};

  return (
    <Shell>
      <div className="space-y-10">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Profile</h1>
            <p className="text-body mt-0.5">Your career profile drives search direction and job matching.</p>
          </div>
          <button
            id="profile-save-btn"
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary btn-sm"
          >
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            {saved ? 'Saved!' : 'Save'}
          </button>
        </div>

        {/* Identity */}
        {personal.name && (
          <div className="flex items-center gap-4">
            <GradientAvatar name={personal.name} size={52} />
            <div>
              <div className="text-lg font-bold" style={{ color: 'var(--text)' }}>{personal.name}</div>
              <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                {personal.email && (
                  <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <Mail size={10} /> {personal.email}
                  </span>
                )}
                {personal.city && (
                  <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                    <MapPin size={10} /> {personal.city}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="divider" />

        {/* Personal + Skills side by side */}
        <div className="grid grid-cols-2 gap-12">
          <div>
            <div className="text-label mb-3">Personal</div>
            {!profile ? (
              <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} height={14} />)}</div>
            ) : (
              <div className="space-y-0">
                {[
                  { label: 'Name',     value: personal.name },
                  { label: 'Email',    value: personal.email },
                  { label: 'Phone',    value: personal.phone },
                  { label: 'LinkedIn', value: personal.linkedin },
                  { label: 'City',     value: personal.city },
                ].filter(f => f.value).map(field => (
                  <div
                    key={field.label}
                    className="flex justify-between py-2"
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{field.label}</span>
                    <span className="text-xs font-medium text-right max-w-[60%] truncate" style={{ color: 'var(--text)' }}>
                      {field.value}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="text-label mb-3">Skills</div>
            {['languages', 'frameworks', 'tools'].map(category => (
              skills[category]?.length > 0 && (
                <div key={category} className="mb-4">
                  <div className="text-[10px] uppercase tracking-wider font-medium mb-2" style={{ color: 'var(--text-faint)' }}>
                    {category}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {skills[category].map((skill: string, i: number) => (
                      <span
                        key={`${category}-${skill}-${i}`}
                        className="text-xs px-2 py-0.5 rounded-md font-medium"
                        style={{
                          background: SKILL_COLORS[category]?.bg || 'var(--surface-2)',
                          color: SKILL_COLORS[category]?.color || 'var(--text-secondary)',
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        </div>

        <div className="divider" />

        {/* Target Roles */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="text-label">Target Roles</div>
            <span className="text-xs tabular-nums" style={{ color: 'var(--text-faint)' }}>
              {selectedRoles.length} selected
            </span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {allRoles.map((role, i) => {
              const checked   = selectedRoles.includes(role);
              const inferred  = inferredRoles.includes(role);
              return (
                <button
                  key={`role-${i}-${role}`}
                  id={`role-toggle-${i}`}
                  onClick={() => toggleRole(role)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-all"
                  style={{
                    background: checked ? 'var(--primary-muted)' : 'transparent',
                    border: `1px solid ${checked ? 'rgba(124,92,252,0.2)' : 'transparent'}`,
                  }}
                  onMouseEnter={e => { if (!checked) e.currentTarget.style.background = 'var(--surface-hover)'; }}
                  onMouseLeave={e => { if (!checked) e.currentTarget.style.background = 'transparent'; }}
                >
                  {checked
                    ? <CheckSquare size={13} style={{ color: 'var(--primary)', flexShrink: 0 }} />
                    : <Square size={13} style={{ color: 'var(--text-faint)', flexShrink: 0 }} />
                  }
                  <span className="text-xs flex-1" style={{ color: checked ? 'var(--text)' : 'var(--text-secondary)' }}>
                    {role}
                  </span>
                  {inferred && (
                    <span
                      className="badge shrink-0"
                      style={{ background: 'var(--primary-subtle)', color: 'var(--primary)', fontSize: 9 }}
                    >
                      <Sparkles size={7} /> AI
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="divider" />

        {/* Target Locations */}
        <div>
          <div className="text-label mb-3">Target Locations</div>
          <div className="flex flex-wrap gap-2">
            {(profile?.job_preferences?.target_locations || []).map((loc: string, i: number) => (
              <span
                key={`loc-${i}`}
                className="text-xs px-2.5 py-1 rounded-full flex items-center gap-1"
                style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              >
                <MapPin size={10} /> {loc}
              </span>
            ))}
            {(profile?.job_preferences?.target_locations || []).length === 0 && (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No target locations configured</p>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
