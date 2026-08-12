'use client';

import { useQuery, useQueries } from '@tanstack/react-query';
import Link from 'next/link';
import { FolderOpen, CalendarDays, FileText, BellRing, Sparkles } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { StatCard, Card, SectionTitle, LoadingState, ErrorState, StatusBadge } from '@/components/ui';
import { casesApi, hearingsApi, notificationsApi, analyticsApi } from '@/lib/services';
import { formatDate, timeAgo } from '@/lib/utils';

export default function LawyerDashboard() {
  const cases = useQuery({ queryKey: ['lawyer-cases'], queryFn: () => casesApi.list().then((r) => r.data) });
  const hearings = useQuery({ queryKey: ['lawyer-hearings'], queryFn: () => hearingsApi.list().then((r) => r.data) });
  const notifs = useQuery({ queryKey: ['lawyer-notifs'], queryFn: () => notificationsApi.list().then((r) => r.data) });

  if (cases.isLoading) return <AppShell><LoadingState /></AppShell>;
  if (cases.error) return <AppShell><ErrorState message="Could not load dashboard" /></AppShell>;

  const myCases = cases.data || [];
  const today = new Date().toISOString().slice(0, 10);
  const todays = (hearings.data || []).filter((h) => h.date === today);
  const upcoming = (hearings.data || []).filter((h) => h.date > today && h.status === 'SCHEDULED');
  const unread = (notifs.data || []).filter((n) => !n.is_read);

  return (
    <AppShell>
      <SectionTitle title="Lawyer Dashboard" subtitle="Your cases and what needs attention" />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="My Cases" value={myCases.length} icon={<FolderOpen size={22} />} />
        <StatCard label="Today's Hearings" value={todays.length} icon={<CalendarDays size={22} />} />
        <StatCard label="Upcoming" value={upcoming.length} icon={<CalendarDays size={22} />} />
        <StatCard label="Unread Notifications" value={unread.length} icon={<BellRing size={22} />} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">My Cases</h3>
            <Link href="/cases" className="text-sm font-medium text-brand-600 hover:underline">View all →</Link>
          </div>
          <ul className="divide-y divide-slate-100">
            {myCases.slice(0, 8).map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <p className="font-medium text-slate-800">
                    <Link href={`/cases/${c.id}`} className="hover:text-brand-600">{c.case_number}</Link>
                    <span className="ml-2 text-slate-500">{c.title}</span>
                  </p>
                  <p className="text-xs text-slate-400">Next hearing: {formatDate(c.next_hearing_date)}</p>
                </div>
                <StatusBadge status={c.status} />
              </li>
            ))}
            {myCases.length === 0 && <p className="py-4 text-sm text-slate-400">No cases assigned yet.</p>}
          </ul>
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700"><FileText size={16} className="mr-1 inline" /> Recent Notifications</h3>
          <ul className="divide-y divide-slate-100">
            {(notifs.data || []).slice(0, 8).map((n) => (
              <li key={n.id} className={`py-2 text-sm ${n.is_read ? 'text-slate-500' : 'font-medium text-slate-800'}`}>
                <p>{n.title}</p>
                <p className="text-xs text-slate-400">{n.message} · {timeAgo(n.created_at)}</p>
              </li>
            ))}
            {(notifs.data || []).length === 0 && <p className="py-4 text-sm text-slate-400">No notifications.</p>}
          </ul>
        </Card>
      </div>

      <WhatChangedStrip cases={myCases} />
    </AppShell>
  );
}

/** What changed since the user's last visit, across their cases (spec §39). */
function WhatChangedStrip({ cases }: { cases: any[] }) {
  const top = cases.slice(0, 6);
  const queries = useQueries({
    queries: top.map((c) => ({
      queryKey: ['what-changed', c.id],
      queryFn: () => analyticsApi.whatChanged(c.id).then((r) => r.data),
      enabled: cases.length > 0,
      staleTime: 60_000,
    })),
  });

  const allChanges = queries.flatMap((q, i) =>
    (q.data?.changes || []).map((ch: string) => ({ text: ch, caseId: top[i]?.id, caseNo: top[i]?.case_number }))
  ).slice(0, 10);

  const anyAI = queries.find((q) => q.data?.ai_summary);

  if (allChanges.length === 0) return null;

  return (
    <Card className="mt-6 border-emerald-100 bg-emerald-50/40">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-emerald-800">
        <Sparkles size={15} /> What changed since your last visit
      </h3>
      <ul className="grid gap-1 text-sm text-slate-700 md:grid-cols-2">
        {allChanges.map((ch, i) => (
          <li key={i} className="flex items-start gap-1.5">
            <span className="mt-1 text-emerald-500">✓</span>
            <span>
              {ch.caseId ? <Link href={`/cases/${ch.caseId}`} className="font-medium text-brand-600 hover:underline">{ch.caseNo}:</Link> : null}{' '}
              {ch.text}
            </span>
          </li>
        ))}
      </ul>
      {anyAI?.data?.ai_summary && (
        <div className="mt-3 rounded-md bg-white p-3 text-sm text-slate-600">
          <span className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase text-slate-400"><Sparkles size={11} /> AI summary</span>
          {anyAI.data.ai_summary}
        </div>
      )}
    </Card>
  );
}
