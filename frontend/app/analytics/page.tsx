'use client';

import { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, CartesianGrid,
} from 'recharts';
import Shell from '@/components/layout/Shell';
import MetricCard from '@/components/ui/MetricCard';
import { getAnalytics, getJobs, getApplications, getRecruiters } from '@/lib/api';
import { Briefcase, Users, FileText, Mail, TrendingUp } from 'lucide-react';

const CHART_COLORS = {
  primary: '#7C5CFC',
  accent:  '#5B8DEF',
  green:   '#34D399',
  amber:   '#FBBF24',
  red:     '#F87171',
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="px-3 py-2 text-xs rounded-lg"
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-lg)',
        color: 'var(--text)',
      }}
    >
      <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color || 'var(--text)' }}>
          {p.value}
        </div>
      ))}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="text-label mb-4">{children}</div>;
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [recruiters, setRecruiters] = useState<any[]>([]);

  useEffect(() => {
    getAnalytics().then(r => setAnalytics(r.analytics)).catch(() => {});
    getJobs().then(r => setJobs(r.jobs || [])).catch(() => {});
    getApplications().then(r => setApplications(r.applications || [])).catch(() => {});
    getRecruiters().then(r => setRecruiters(r.recruiters || [])).catch(() => {});
  }, []);

  const a = analytics || {};

  const funnelData = useMemo(() => {
    const found     = a.total_jobs || 0;
    const drafted   = a.applications_drafted || 0;
    const submitted = a.applications_submitted || 0;
    const emails    = a.emails_sent || 0;
    return [
      { name: 'Discovered', value: found,     fill: CHART_COLORS.accent },
      { name: 'Drafted',    value: drafted,   fill: CHART_COLORS.primary },
      { name: 'Submitted',  value: submitted, fill: CHART_COLORS.green },
      { name: 'Emailed',    value: emails,    fill: CHART_COLORS.amber },
    ];
  }, [a]);

  const scoreData = useMemo(() => {
    const buckets = [
      { name: '80+',   value: 0, fill: CHART_COLORS.green },
      { name: '60–79', value: 0, fill: CHART_COLORS.accent },
      { name: '40–59', value: 0, fill: CHART_COLORS.amber },
      { name: '<40',   value: 0, fill: CHART_COLORS.red },
    ];
    jobs.forEach(j => {
      const s = j.fit_score;
      if (s == null) return;
      if (s >= 80)       buckets[0].value++;
      else if (s >= 60)  buckets[1].value++;
      else if (s >= 40)  buckets[2].value++;
      else               buckets[3].value++;
    });
    return buckets;
  }, [jobs]);

  const sourceData = useMemo(() => {
    const counts: Record<string, number> = {};
    jobs.forEach(j => { counts[j.source || 'unknown'] = (counts[j.source || 'unknown'] || 0) + 1; });
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6)
      .map(([name, value]) => ({ name, value }));
  }, [jobs]);

  const appStatusData = useMemo(() => {
    const counts: Record<string, number> = {};
    applications.forEach(app => {
      const key = (app.application_status || 'saved').toLowerCase();
      counts[key] = (counts[key] || 0) + 1;
    });
    const PIE_COLORS = [CHART_COLORS.primary, CHART_COLORS.accent, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.red];
    return Object.entries(counts).map(([name, value], i) => ({
      name: name.replace(/_/g, ' '),
      value,
      fill: PIE_COLORS[i % PIE_COLORS.length],
    }));
  }, [applications]);

  const avgScore = useMemo(() => {
    const scored = jobs.filter(j => j.fit_score != null);
    if (scored.length === 0) return 0;
    return Math.round(scored.reduce((sum, j) => sum + j.fit_score, 0) / scored.length);
  }, [jobs]);

  const metrics = [
    { label: 'Jobs Found',   value: a.total_jobs ?? 0,              icon: <Briefcase size={14} style={{ color: 'var(--accent)' }} />,  color: 'var(--accent)',  delay: 0 },
    { label: 'Drafted',      value: a.applications_drafted ?? 0,    icon: <FileText size={14} style={{ color: 'var(--primary)' }} />,  color: 'var(--primary)', delay: 0.05 },
    { label: 'Submitted',    value: a.applications_submitted ?? 0,  icon: <TrendingUp size={14} style={{ color: 'var(--green)' }} />,  color: 'var(--green)',   delay: 0.1 },
    { label: 'Emails Sent',  value: a.emails_sent ?? 0,             icon: <Mail size={14} style={{ color: 'var(--amber)' }} />,        color: 'var(--amber)',   delay: 0.15 },
    { label: 'Recruiters',   value: recruiters.length,              icon: <Users size={14} style={{ color: 'var(--cyan)' }} />,        color: 'var(--cyan)',    delay: 0.2 },
  ];

  const chartStyle = {
    fontSize: 11,
    fontFamily: 'Inter, sans-serif',
  };

  return (
    <Shell>
      <div className="space-y-10">
        {/* Header */}
        <div>
          <h1 className="text-page-title">Analytics</h1>
          <p className="text-body mt-0.5">Performance insights across your pipeline.</p>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {metrics.map(m => (
            <MetricCard key={m.label} label={m.label} value={m.value} icon={m.icon} color={m.color} delay={m.delay} />
          ))}
        </div>

        <div className="divider" />

        {/* Charts row 1: Funnel + Score distribution */}
        <div className="grid grid-cols-2 gap-12">
          {/* Funnel — horizontal bar chart */}
          <div>
            <SectionLabel>Application Funnel</SectionLabel>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={funnelData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={70}
                  tick={{ fill: 'var(--text-muted)', ...chartStyle }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {funnelData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Score distribution — vertical bar chart */}
          <div>
            <SectionLabel>
              Score Distribution
              <span className="ml-2 text-2xl font-bold tabular-nums" style={{ color: 'var(--text)', textTransform: 'none', letterSpacing: 'normal' }}>
                {avgScore}
                <span className="text-xs font-normal ml-1" style={{ color: 'var(--text-muted)' }}>avg</span>
              </span>
            </SectionLabel>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={scoreData} margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: 'var(--text-muted)', ...chartStyle }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {scoreData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="divider" />

        {/* Charts row 2: Source + Application status */}
        <div className="grid grid-cols-2 gap-12">
          {/* Jobs by source — horizontal bar */}
          <div>
            <SectionLabel>Jobs by Source</SectionLabel>
            {sourceData.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No data yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(120, sourceData.length * 36)}>
                <BarChart data={sourceData} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={80}
                    tick={{ fill: 'var(--text-muted)', ...chartStyle }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                  <Bar dataKey="value" fill={CHART_COLORS.accent} fillOpacity={0.8} radius={[0, 4, 4, 0]} maxBarSize={16} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Application status — donut chart */}
          <div>
            <SectionLabel>Application Status</SectionLabel>
            {appStatusData.length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No applications tracked</p>
            ) : (
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={140} height={140}>
                  <PieChart>
                    <Pie
                      data={appStatusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={65}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {appStatusData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1.5">
                  {appStatusData.map((entry, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: entry.fill }} />
                      <span className="text-xs capitalize" style={{ color: 'var(--text-secondary)' }}>{entry.name}</span>
                      <span className="text-xs font-bold tabular-nums ml-auto" style={{ color: 'var(--text)' }}>{entry.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
