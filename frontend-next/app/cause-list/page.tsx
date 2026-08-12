'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, StatusBadge } from '@/components/ui';
import { analyticsApi } from '@/lib/services';
import { formatDate } from '@/lib/utils';

export default function CauseListPage() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [courtroom, setCourtroom] = useState('');
  const { data, isLoading, error } = useQuery({
    queryKey: ['cause-list', date, courtroom],
    queryFn: () => analyticsApi.causeList(date, courtroom || undefined).then((r) => r.data),
  });

  return (
    <AppShell>
      <SectionTitle title="Cause List" subtitle="Court schedule — filter by date or courtroom (spec §26)" />
      <Card className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label" htmlFor="cl-date">Date</label>
            <input id="cl-date" type="date" className="input sm:w-52" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="cl-courtroom">Courtroom</label>
            <input id="cl-courtroom" className="input sm:w-56" placeholder="e.g. Courtroom 1" value={courtroom} onChange={(e) => setCourtroom(e.target.value)} />
          </div>
        </div>
      </Card>
      {isLoading && <LoadingState />}
      {error && <ErrorState message="Could not load cause list" />}
      {data && (
        <Card>
          <p className="mb-3 text-sm text-slate-500">{data.count} hearing(s) on {formatDate(date)}</p>
          {data.hearings.length === 0 && <p className="py-8 text-center text-sm text-slate-400">No hearings on this date.</p>}
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead><tr><th>#</th><th>Case</th><th>Time</th><th>Courtroom</th><th>Purpose</th><th>Status</th></tr></thead>
              <tbody>
                {data.hearings.map((h: any) => (
                  <tr key={h.id}>
                    <td>#{h.hearing_number}</td>
                    <td className="font-medium text-brand-600"><Link href={`/cases/${h.case}`}>{h.case_number || h.case}</Link></td>
                    <td>{h.start_time || '—'}</td>
                    <td>{h.courtroom_name || '—'}</td>
                    <td className="max-w-[280px] truncate">{h.purpose || '—'}</td>
                    <td><StatusBadge status={h.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </AppShell>
  );
}
