'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { CalendarDays, Clock, AlertCircle, FileText, Scale, ScrollText } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { StatCard, Card, SectionTitle, LoadingState, ErrorState, StatusBadge } from '@/components/ui';
import { hearingsApi, casesApi, analyticsApi, ordersApi, unwrapList } from '@/lib/services';
import { formatDate } from '@/lib/utils';

export default function JudgeDashboard() {
  const today = new Date().toISOString().slice(0, 10);

  const hearings = useQuery({ queryKey: ['judge-hearings'], queryFn: () => hearingsApi.list({}).then((r) => r.data) });
  const cases = useQuery({ queryKey: ['judge-cases'], queryFn: () => casesApi.list().then((r) => r.data) });
  const causeList = useQuery({ queryKey: ['cause-list', today], queryFn: () => analyticsApi.causeList(today).then((r) => r.data) });
  const orders = useQuery({ queryKey: ['judge-orders'], queryFn: () => ordersApi.list().then((r) => r.data) });

  if (hearings.isLoading || cases.isLoading) return <AppShell><LoadingState /></AppShell>;
  if (hearings.error) return <AppShell><ErrorState message="Could not load dashboard" /></AppShell>;

  const allHearings = unwrapList(hearings.data);
  const todays = allHearings.filter((h) => h.date === today);
  const upcoming = allHearings.filter((h) => h.date > today && h.status === 'SCHEDULED');
  const allCases = unwrapList(cases.data);
  const pending = allCases.filter((c) => ['PENDING', 'FILED', 'REGISTERED'].includes(c.status));
  const urgent = allCases.filter((c) => c.priority === 'URGENT');
  const ordersPending = unwrapList(orders.data).filter((o) => o.status === 'DRAFT').length;

  return (
    <AppShell>
      <SectionTitle title="Judge Dashboard" subtitle={`Today: ${formatDate(today)}`} />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Today's Hearings" value={todays.length} icon={<CalendarDays size={22} />} />
        <StatCard label="Upcoming Hearings" value={upcoming.length} icon={<Clock size={22} />} />
        <StatCard label="Pending Cases" value={pending.length} icon={<Scale size={22} />} />
        <StatCard label="Urgent Cases" value={urgent.length} icon={<AlertCircle size={22} />} />
      </div>
      <div className="mt-4">
        <StatCard label="Orders Pending (draft)" value={ordersPending} icon={<ScrollText size={22} />} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Today's Hearings (Cause List)</h3>
          {(causeList.data?.hearings || []).length === 0 && <p className="text-sm text-slate-400">No hearings scheduled today.</p>}
          <ul className="divide-y divide-slate-100">
            {(causeList.data?.hearings || []).map((h: any) => (
              <li key={h.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <p className="font-medium text-slate-800">
                    <Link href={`/cases/${h.case}`} className="hover:text-brand-600">Hearing #{h.hearing_number}</Link>
                    <span className="ml-2 text-slate-500">{h.case_number ? '' : ''}{h.purpose}</span>
                  </p>
                  <p className="text-xs text-slate-400">{h.start_time || '—'} · {h.courtroom_name || 'Courtroom'}</p>
                </div>
                <StatusBadge status={h.status} />
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Upcoming Hearings</h3>
          {upcoming.length === 0 && <p className="text-sm text-slate-400">No upcoming hearings.</p>}
          <ul className="divide-y divide-slate-100">
            {upcoming.slice(0, 8).map((h) => (
              <li key={h.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <p className="font-medium text-slate-800">
                    <Link href={`/cases/${h.case}`} className="hover:text-brand-600">Hearing #{h.hearing_number}</Link>
                  </p>
                  <p className="text-xs text-slate-400">{formatDate(h.date)} {h.start_time ? `· ${h.start_time}` : ''}</p>
                </div>
                <StatusBadge status={h.status} />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700"><FileText size={16} className="mr-1 inline" /> My Cases</h3>
            <Link href="/cases" className="text-sm font-medium text-brand-600 hover:underline">View all →</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr><th>Case</th><th>Title</th><th>Status</th><th>Next Hearing</th></tr>
              </thead>
              <tbody>
                {allCases.slice(0, 10).map((c) => (
                  <tr key={c.id}>
                    <td className="font-medium text-brand-600"><Link href={`/cases/${c.id}`}>{c.case_number}</Link></td>
                    <td className="max-w-[240px] truncate">{c.title}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td>{formatDate(c.next_hearing_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
