'use client';

import ProgressBar from '@/components/ui/ProgressBar';

interface Props {
  match: any;
}

export default function MatchScoreCard({ match }: Props) {
  if (!match) return null;

  const breakdowns = [
    { label: 'Skills Match', value: match.skills_score ?? match.skill_match ?? 0 },
    { label: 'Experience', value: match.experience_score ?? match.experience_match ?? 0 },
    { label: 'Education', value: match.education_score ?? match.education_match ?? 0 },
    { label: 'Overall', value: match.overall_score ?? match.fit_score ?? 0 },
  ].filter(b => b.value > 0);

  return (
    <div
      className="rounded-lg p-4 space-y-3"
      style={{ background: 'var(--surface)', border: '1px solid var(--border-subtle)' }}
    >
      <div className="text-label">Match Breakdown</div>
      {breakdowns.map((item) => (
        <div key={item.label}>
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
            <span className="font-medium tabular-nums" style={{ color: 'var(--text-muted)' }}>
              {item.value}/100
            </span>
          </div>
          <ProgressBar value={item.value} height={4} />
        </div>
      ))}
    </div>
  );
}
