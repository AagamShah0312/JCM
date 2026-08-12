'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { FolderOpen, Scale, CheckCircle2, Clock, AlertTriangle, BarChart3, Upload, Users } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { StatCard, Card, SectionTitle, LoadingState, ErrorState } from '@/components/ui';
import { analyticsApi } from '@/lib/services';

export default function AdminDashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['admin-analytics'], queryFn: () => analyticsApi.admin().then((r) => r.data) });

  if (isLoading) return <AppShell><LoadingState label="Loading dashboard…" /></AppShell>;
  if (error) return <AppShell><ErrorState message="Could not load analytics" /></AppShell>;

  const stats = data?.case_stats || {};
  const attention = data?.attention || {};

  return (
    <AppShell>
      <SectionTitle title="Admin Dashboard" subtitle="System-wide overview across the court" />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total Cases" value={stats.total_cases ?? '—'} icon={<FolderOpen size={22} />} />
        <StatCard label="Active" value={stats.active ?? '—'} icon={<Scale size={22} />} />
        <StatCard label="Pending" value={stats.pending ?? '—'} icon={<Clock size={22} />} />
        <StatCard label="Closed / Disposed" value={(stats.closed ?? 0) + (stats.disposed ?? 0)} icon={<CheckCircle2 size={22} />} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><BarChart3 size={16} /> Cases by Type</h3>
          <ul className="space-y-2 text-sm">
            {(data?.cases_by_type || []).slice(0, 8).map((t: any) => (
              <li key={t.case_type} className="flex justify-between">
                <span className="text-slate-600">{t.case_type || '—'}</span>
                <span className="font-semibold">{t.count}</span>
              </li>
            ))}
            {(data?.cases_by_type || []).length === 0 && <li className="text-slate-400">No data</li>}
          </ul>
        </Card>

        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><Clock size={16} /> Case Age Distribution</h3>
          <ul className="space-y-2 text-sm">
            {Object.entries(data?.case_age_distribution || {}).map(([bucket, count]) => (
              <li key={bucket} className="flex justify-between">
                <span className="text-slate-600">{bucket === '10+None' ? '10+ years' : `${bucket} years`}</span>
                <span className="font-semibold">{String(count)}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-600"><AlertTriangle size={16} /> Needs Attention</h3>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between"><span className="text-slate-600">Cases &gt; 5 years old</span><span className="font-semibold">{attention.cases_older_than_5_years ?? 0}</span></li>
            <li className="flex justify-between"><span className="text-slate-600">Long gap since hearing</span><span className="font-semibold">{attention.cases_with_long_gap_since_hearing ?? 0}</span></li>
            <li className="text-slate-600">High adjournment count: <span className="font-semibold">{(attention.cases_with_high_adjournment_count || []).length}</span></li>
          </ul>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Link href="/admin/analytics" className="btn-secondary w-full text-center">Analytics</Link>
            <Link href="/admin/csv" className="btn-secondary w-full text-center"><Upload size={14} className="mr-1 inline" /> CSV Import</Link>
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><Scale size={16} /> Cases by Court</h3>
          <ul className="space-y-2 text-sm">
            {(data?.cases_by_court || []).slice(0, 6).map((c: any) => (
              <li key={c.court__name} className="flex justify-between">
                <span className="text-slate-600">{c.court__name}</span>
                <span className="font-semibold">{c.count}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><Users size={16} /> Quick Actions</h3>
          <div className="grid grid-cols-2 gap-2">
            <Link href="/cases" className="btn-secondary text-center">Manage Cases</Link>
            <Link href="/admin/users" className="btn-secondary text-center">Manage Users</Link>
            <Link href="/admin/courts" className="btn-secondary text-center">Courts &amp; Courtrooms</Link>
            <Link href="/cause-list" className="btn-secondary text-center">Cause List</Link>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
