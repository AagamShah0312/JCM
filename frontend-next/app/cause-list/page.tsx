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
  const { data, isLoading, error } = useQuery({
    queryKey: ['cause-list', date],
    queryFn: () => analyticsApi.causeList(date).then((r) => r.data),
  });

  return (
    <AppShell>
      <SectionTitle title="Cause List" subtitle="Today's court schedule" />
      <Card className="mb-4">
        <label className="label">Date</label>
        <input type="date" className="input sm:w-52" value={date} onChange={(e) => setDate(e.target.value)} />
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
