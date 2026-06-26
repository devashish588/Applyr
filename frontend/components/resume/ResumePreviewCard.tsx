'use client';

import { motion } from 'framer-motion';
import { User, Mail, Phone, GraduationCap, Briefcase, Code2 } from 'lucide-react';

interface ParsedResume {
  name?: string;
  email?: string;
  phone?: string;
  education?: Array<{ summary?: string }>;
  experience?: Array<{ title?: string; company?: string; bullets?: string[] }>;
  skills?: string[];
}

interface Props {
  data: ParsedResume | null;
}

export default function ResumePreviewCard({ data }: Props) {
  if (!data) return null;

  const sections = [
    { icon: User, label: 'Name', value: data.name },
    { icon: Mail, label: 'Email', value: data.email },
    { icon: Phone, label: 'Phone', value: data.phone },
  ].filter(s => s.value);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="card p-5"
    >
      <div className="text-label mb-4">Resume Preview</div>

      <div className="space-y-3">
        {sections.map((s, i) => (
          <div key={i} className="flex items-center gap-3 py-1.5">
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center"
              style={{ background: 'var(--primary-muted)' }}
            >
              <s.icon size={14} style={{ color: 'var(--primary)' }} />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: 'var(--text-faint)' }}>
                {s.label}
              </div>
              <div className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                {s.value}
              </div>
            </div>
          </div>
        ))}

        {/* Education */}
        {data.education && data.education.length > 0 && (
          <div className="pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            <div className="flex items-center gap-2 mb-2">
              <GraduationCap size={13} style={{ color: 'var(--primary)' }} />
              <span className="text-label" style={{ fontSize: 10 }}>Education</span>
            </div>
            {data.education.map((ed, i) => (
              <div key={i} className="text-xs py-1 pl-6" style={{ color: 'var(--text-secondary)' }}>
                {ed.summary}
              </div>
            ))}
          </div>
        )}

        {/* Experience */}
        {data.experience && data.experience.length > 0 && (
          <div className="pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            <div className="flex items-center gap-2 mb-2">
              <Briefcase size={13} style={{ color: 'var(--amber)' }} />
              <span className="text-label" style={{ fontSize: 10 }}>Experience</span>
            </div>
            {data.experience.slice(0, 2).map((exp, i) => (
              <div key={i} className="pl-6 mb-2">
                <div className="text-xs font-medium" style={{ color: 'var(--text)' }}>
                  {exp.title}{exp.company ? ` at ${exp.company}` : ''}
                </div>
                {exp.bullets?.slice(0, 2).map((b, j) => (
                  <div key={j} className="text-xs py-0.5" style={{ color: 'var(--text-muted)' }}>
                    • {b.length > 80 ? b.slice(0, 80) + '...' : b}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Skills */}
        {data.skills && data.skills.length > 0 && (
          <div className="pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            <div className="flex items-center gap-2 mb-2">
              <Code2 size={13} style={{ color: 'var(--green)' }} />
              <span className="text-label" style={{ fontSize: 10 }}>Skills</span>
            </div>
            <div className="flex flex-wrap gap-1.5 pl-6">
              {data.skills.map((skill, i) => (
                <span key={i} className="badge badge-neutral">{skill}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
