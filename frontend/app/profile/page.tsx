'use client';

import { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { User, Briefcase, MapPin, Code2, CheckSquare, Square, Save, Loader2 } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { Skeleton } from '@/components/ui/Skeleton';
import { getProfile, updateProfile, getResumeParsed } from '@/lib/api';

const DEFAULT_ROLES = [
  'Machine Learning Engineer', 'Data Scientist', 'AI Engineer',
  'Data Analyst', 'ML Intern', 'Full Stack Developer',
  'Backend Engineer', 'Software Engineer', 'DevOps Engineer',
  'Frontend Developer',
];

function extractRoleString(item: any): string {
  if (typeof item === 'string') return item;
  if (item && typeof item === 'object' && item.role) return String(item.role);
  return String(item);
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [resumeData, setResumeData] = useState<any>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

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

  const toggleRole = (role: string) => setSelectedRoles(prev => prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]);

  const handleSave = async () => {
    setSaving(true);
    try { await updateProfile({ target_roles: selectedRoles }); } catch {}
    setSaving(false);
  };

  const personal = profile?.personal || {};
  const skills = profile?.skills || {};

  return (
    <Shell>
      <div className="space-y-10">
        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-page-title">Profile</h1>
            <p className="text-body mt-0.5">Your career profile drives search direction and job matching.</p>
          </div>
          <button onClick={handleSave} disabled={saving} className="btn btn-primary btn-sm">
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            Save
          </button>
        </div>

        {/* Identity — flat, no card */}
        {personal.name && (
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold"
              style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}
            >
              {personal.name[0]?.toUpperCase()}
            </div>
            <div>
              <div className="text-base font-semibold" style={{ color: 'var(--text)' }}>{personal.name}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {personal.email || ''}{personal.city ? ` · ${personal.city}` : ''}
              </div>
            </div>
          </div>
        )}

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Personal + Skills side by side — flat */}
        <div className="grid grid-cols-2 gap-12">
          <div>
            <div className="text-label mb-3">Personal</div>
            {!profile ? (
              <div className="space-y-2">{[1,2,3,4].map(i => <Skeleton key={i} height={14} />)}</div>
            ) : (
              <div className="space-y-0">
                {[
                  { label: 'Name', value: personal.name },
                  { label: 'Email', value: personal.email },
                  { label: 'Phone', value: personal.phone },
                  { label: 'LinkedIn', value: personal.linkedin },
                  { label: 'City', value: personal.city },
                ].filter(f => f.value).map(field => (
                  <div key={field.label} className="flex justify-between py-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{field.label}</span>
                    <span className="text-xs font-medium text-right max-w-[60%] truncate" style={{ color: 'var(--text)' }}>{field.value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="text-label mb-3">Skills</div>
            {['languages', 'frameworks', 'tools'].map(category => (
              skills[category]?.length > 0 && (
                <div key={category} className="mb-3">
                  <div className="text-[10px] uppercase tracking-wider font-medium mb-1.5" style={{ color: 'var(--text-faint)' }}>
                    {category}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {skills[category].map((skill: string, i: number) => (
                      <span key={`${category}-${skill}-${i}`} className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Target Roles — grid of toggles, no card wrapper */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="text-label">Target Roles</div>
            <span className="text-xs tabular-nums" style={{ color: 'var(--text-faint)' }}>{selectedRoles.length} selected</span>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {allRoles.map((role, i) => {
              const checked = selectedRoles.includes(role);
              const inferred = inferredRoles.includes(role);
              return (
                <button
                  key={`role-${i}-${role}`}
                  onClick={() => toggleRole(role)}
                  className="flex items-center gap-2 px-2.5 py-2 rounded-md text-left transition-all"
                  style={{
                    background: checked ? 'var(--primary-muted)' : 'transparent',
                  }}
                  onMouseEnter={e => { if (!checked) e.currentTarget.style.background = 'var(--surface-hover)'; }}
                  onMouseLeave={e => { if (!checked) e.currentTarget.style.background = 'transparent'; }}
                >
                  {checked
                    ? <CheckSquare size={13} style={{ color: 'var(--primary)' }} />
                    : <Square size={13} style={{ color: 'var(--text-faint)' }} />
                  }
                  <span className="text-xs flex-1" style={{ color: checked ? 'var(--text)' : 'var(--text-secondary)' }}>
                    {role}
                  </span>
                  {inferred && <span className="text-[9px]" style={{ color: 'var(--text-faint)' }}>AI</span>}
                </button>
              );
            })}
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Locations — flat */}
        <div>
          <div className="text-label mb-3">Locations</div>
          <div className="flex flex-wrap gap-1.5">
            {(profile?.job_preferences?.target_locations || []).map((loc: string, i: number) => (
              <span key={`loc-${i}`} className="text-xs px-2 py-1 rounded" style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)' }}>{loc}</span>
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
