'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Gavel } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, EmptyState } from '@/components/ui';
import api from '@/lib/api';
import { unwrapList } from '@/lib/services';

export default function CourtsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['courts'], queryFn: () => api.get('/courts/').then((r) => r.data) });

  return (
    <AppShell>
      <SectionTitle title="Courts & Courtrooms" subtitle="Manage courts and their courtrooms" />
      {isLoading && <LoadingState />}
      {error && <ErrorState message="Could not load courts" />}
      {data && data.length === 0 && <EmptyState title="No courts" message="Add courts to organize cases." />}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.map((court: any) => (
          <Card key={court.id}>
            <div className="flex items-start gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-50 text-brand-600"><Gavel size={18} /></div>
              <div>
                <p className="font-semibold text-slate-800">{court.name}</p>
                <p className="text-xs text-slate-400">{court.court_type} · {court.city} {court.state}</p>
              </div>
            </div>
            <div className="mt-3">
              <p className="mb-1 text-xs font-semibold uppercase text-slate-400">Courtrooms ({court.courtrooms?.length || 0})</p>
              <ul className="space-y-1 text-sm">
                {(court.courtrooms || []).map((r: any) => (
                  <li key={r.id} className="flex justify-between text-slate-600">
                    <span>{r.name}</span>
                    <span className="text-xs text-slate-400">{r.capacity || ''} {r.floor ? `· ${r.floor}` : ''}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
