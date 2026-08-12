'use client';

import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell, Legend,
} from 'recharts';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, StatCard } from '@/components/ui';
import { analyticsApi } from '@/lib/services';

const COLORS = ['#1f43f0', '#5b8bfe', '#8fb4ff', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444', '#64748b'];

export default function AdminAnalyticsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['admin-analytics'], queryFn: () => analyticsApi.admin().then((r) => r.data) });

  if (isLoading) return <AppShell><LoadingState /></AppShell>;
  if (error) return <AppShell><ErrorState message="Could not load analytics" /></AppShell>;

  const stats = data?.case_stats || {};
  const byType = (data?.cases_by_type || []).map((t: any) => ({ name: t.case_type || 'Other', value: t.count }));
  const byCourt = (data?.cases_by_court || []).map((c: any) => ({ name: c.court__name || '—', value: c.count }));
  const ageDist = Object.entries(data?.case_age_distribution || {}).map(([k, v]) => ({
    name: k === '10+None' ? '10+' : `${k}y`, value: Number(v),
  }));
  const adj = data?.adjournment_analytics?.by_reason || [];

  return (
    <AppShell>
      <SectionTitle title="System Analytics" subtitle="Administrative visibility — not judicial evaluation" />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total Cases" value={stats.total_cases ?? 0} />
        <StatCard label="Active" value={stats.active ?? 0} />
        <StatCard label="Pending" value={stats.pending ?? 0} />
        <StatCard label="Disposed" value={stats.disposed ?? 0} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Cases by Type</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={byType}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#1f43f0" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Case Age Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={ageDist} dataKey="value" nameKey="name" outerRadius={90} label>
                {ageDist.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Cases by Court</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={byCourt} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#5b8bfe" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Adjournments by Reason</h3>
          {adj.length === 0 ? <p className="text-sm text-slate-400">No adjournment data yet.</p> : (
            <ul className="space-y-2 text-sm">
              {adj.map((a: any) => (
                <li key={a.code} className="flex items-center justify-between">
                  <span className="text-slate-600">{a.label || a.code}</span>
                  <span className="font-semibold">{a.count}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
