'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search, FolderOpen, FileText, CalendarDays, ScrollText, Loader2 } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, StatusBadge, EmptyState, Badge } from '@/components/ui';
import { searchApi } from '@/lib/services';
import { formatDate } from '@/lib/utils';

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [submitted, setSubmitted] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['global-search', submitted],
    queryFn: () => searchApi.global(submitted).then((r) => r.data),
    enabled: submitted.length >= 2,
  });

  const run = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(q.trim());
  };

  return (
    <AppShell>
      <SectionTitle title="Global Search" subtitle="Search across cases, documents, hearings and orders (authorized results only)" />

      <form onSubmit={run} className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-10"
            placeholder="Search case number, CNR, party, title, document…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            minLength={2}
            aria-label="Global search"
          />
        </div>
        <button className="btn-primary" disabled={q.trim().length < 2}>Search</button>
      </form>

      {isLoading && (
        <div className="flex items-center justify-center py-12 text-slate-500">
          <Loader2 size={20} className="mr-2 animate-spin" /> Searching…
        </div>
      )}
      {error && <EmptyState title="Search failed" message="Try again with a different query." />}

      {data && !isLoading && (
        <div className="grid gap-4 lg:grid-cols-2">
          <ResultsCard
            title="Cases" count={data.cases?.length} icon={<FolderOpen size={16} />}
            empty="No matching cases."
          >
            {(data.cases || []).map((c: any) => (
              <li key={c.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <Link href={`/cases/${c.id}`} className="font-medium text-brand-600 hover:underline">{c.case_number}</Link>
                  <span className="ml-2 text-slate-600">{c.title}</span>
                  <p className="text-xs text-slate-400">{c.case_type} · Filed {formatDate(c.filing_date)}</p>
                </div>
                <StatusBadge status={c.status} />
              </li>
            ))}
          </ResultsCard>

          <ResultsCard
            title="Documents" count={data.documents?.length} icon={<FileText size={16} />}
            empty="No matching documents."
          >
            {(data.documents || []).map((d: any) => (
              <li key={d.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <Link href={`/cases/${d.case}`} className="font-medium text-slate-700 hover:text-brand-600">{d.file_name}</Link>
                  <p className="text-xs text-slate-400">{d.document_type} · {formatDate(d.uploaded_at)}</p>
                </div>
                <Badge tone={d.visibility === 'PUBLIC' ? 'green' : 'slate'}>{d.visibility}</Badge>
              </li>
            ))}
          </ResultsCard>

          <ResultsCard
            title="Hearings" count={data.hearings?.length} icon={<CalendarDays size={16} />}
            empty="No matching hearings."
          >
            {(data.hearings || []).map((h: any) => (
              <li key={h.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <Link href={`/cases/${h.case}`} className="font-medium text-slate-700 hover:text-brand-600">Hearing #{h.hearing_number}</Link>
                  <p className="text-xs text-slate-400">{formatDate(h.date)} {h.purpose ? `· ${h.purpose}` : ''}</p>
                </div>
                <StatusBadge status={h.status} />
              </li>
            ))}
          </ResultsCard>

          <ResultsCard
            title="Orders" count={data.orders?.length} icon={<ScrollText size={16} />}
            empty="No matching orders."
          >
            {(data.orders || []).map((o: any) => (
              <li key={o.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <Link href={`/cases/${o.case}`} className="font-medium text-slate-700 hover:text-brand-600">{o.title}</Link>
                  <p className="text-xs text-slate-400">{o.order_type} · {formatDate(o.date)}</p>
                </div>
                <StatusBadge status={o.status} />
              </li>
            ))}
          </ResultsCard>
        </div>
      )}
    </AppShell>
  );
}

function ResultsCard({ title, count, icon, children, empty }: {
  title: string; count: number; icon: React.ReactNode; children: React.ReactNode; empty: string;
}) {
  return (
    <Card>
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700">
        {icon} {title} <Badge tone="blue">{count ?? 0}</Badge>
      </h3>
      {count ? <ul className="divide-y divide-slate-100">{children}</ul> : <p className="text-sm text-slate-400">{empty}</p>}
    </Card>
  );
}
