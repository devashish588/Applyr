'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { User, Briefcase, MapPin, Code2, CheckSquare, Square, Save, Loader2 } from 'lucide-react';
import Shell from '@/components/layout/Shell';
import { getProfile, updateProfile, getResumeParsed } from '@/lib/api';

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
    getResumeParsed().then(r => {
      if (r.success) setResumeData(r);
    }).catch(() => {});
  }, []);

  const allRoles = [
    ...new Set([
      ...(resumeData?.roles_json || []),
      ...(profile?.job_preferences?.target_roles || []),
      'Machine Learning Engineer', 'Data Scientist', 'AI Engineer',
      'Data Analyst', 'ML Intern', 'Full Stack Developer',
      'Backend Engineer', 'Software Engineer', 'DevOps Engineer',
      'Frontend Developer',
    ])
  ];

  const toggleRole = (role: string) => {
    setSelectedRoles(prev =>
      prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateProfile({ target_roles: selectedRoles });
    } catch {}
    setSaving(false);
  };

  const personal = profile?.personal || {};
  const skills = profile?.skills || {};
  const allSkills = [
    ...(skills.languages || []),
    ...(skills.frameworks || []),
    ...(skills.tools || []),
  ];

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold" style={{ color: 'var(--text)' }}>Profile</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              Your career profile — controls search direction
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{ background: 'var(--accent)', color: '#fff' }}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>

        <div className="grid grid-cols-2 gap-5">
          {/* Personal Info */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl p-5 card-hover"
            style={{ background: 'var(--surface)' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <User size={12} style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>
                Personal Info
              </span>
            </div>

            <div className="space-y-3">
              {[
                { label: 'Name', value: personal.name },
                { label: 'Email', value: personal.email },
                { label: 'Phone', value: personal.phone },
                { label: 'LinkedIn', value: personal.linkedin },
                { label: 'City', value: personal.city },
              ].filter(f => f.value).map((field, i) => (
                <div key={i} className="flex justify-between py-1.5 border-b"
                     style={{ borderColor: 'var(--border)' }}>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{field.label}</span>
                  <span className="text-xs font-medium" style={{ color: 'var(--text)' }}>{field.value}</span>
                </div>
              ))}
              {profile?.experience_summary && (
                <div className="pt-2">
                  <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                    Experience Level
                  </span>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                    {profile.experience_summary}
                  </p>
                </div>
              )}
            </div>
          </motion.div>

          {/* Top Skills */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="rounded-xl p-5 card-hover"
            style={{ background: 'var(--surface)' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Code2 size={12} style={{ color: 'var(--green)' }} />
              <span className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)' }}>
                Skills
              </span>
            </div>

            {['languages', 'frameworks', 'tools'].map((category) => (
              skills[category] && skills[category].length > 0 && (
                <div key={category} className="mb-3">
                  <div className="text-[10px] uppercase tracking-wider font-semibold mb-1.5"
                       style={{ color: 'var(--text-muted)' }}>
                    {category}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {skills[category].map((skill: string, i: number) => (
                      <span key={i} className="text-[11px] px-2 py-0.5 rounded-md"
                            style={{ background: 'var(--surface-2)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )
            ))}
          </motion.div>
        </div>

        {/* Role Selector */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-xl p-5 card-hover"
          style={{ background: 'var(--surface)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Briefcase size={12} style={{ color: 'var(--purple)' }} />
            <span className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--text-muted)' }}>
              Preferred Roles
            </span>
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded"
                  style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}>
              {selectedRoles.length} selected
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {allRoles.map((role) => {
              const checked = selectedRoles.includes(role);
              const inferred = resumeData?.roles_json?.includes(role);
              return (
                <button
                  key={role}
                  onClick={() => toggleRole(role)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all"
                  style={{
                    background: checked ? 'var(--accent-muted)' : 'var(--surface-2)',
                    border: `1px solid ${checked ? 'var(--accent)' : 'var(--border)'}`,
                  }}
                >
                  {checked ? (
                    <CheckSquare size={14} style={{ color: 'var(--accent)' }} />
                  ) : (
                    <Square size={14} style={{ color: 'var(--text-muted)' }} />
                  )}
                  <span className="text-sm" style={{ color: checked ? 'var(--text)' : 'var(--text-secondary)' }}>
                    {role}
                  </span>
                  {inferred && (
                    <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded"
                          style={{ background: 'var(--purple-muted)', color: 'var(--purple)' }}>
                      AI
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </motion.div>

        {/* Target Locations */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-xl p-5 card-hover"
          style={{ background: 'var(--surface)' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={12} style={{ color: 'var(--green)' }} />
            <span className="text-xs font-semibold uppercase tracking-wider"
                  style={{ color: 'var(--text-muted)' }}>
              Target Locations
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {(profile?.job_preferences?.target_locations || []).map((loc: string, i: number) => (
              <span key={i} className="text-sm px-3 py-1.5 rounded-lg"
                    style={{ background: 'var(--green-muted)', color: 'var(--green)', border: '1px solid rgba(34,197,94,0.2)' }}>
                {loc}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </Shell>
  );
}
