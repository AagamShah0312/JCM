'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Scale, FileText, ScrollText, CalendarDays, Info } from 'lucide-react';
import { Card, StatusBadge, LoadingState, ErrorState } from '@/components/ui';
import { publicApi } from '@/lib/services';
import { formatDate } from '@/lib/utils';

export default function PublicCasePage() {
  const { id } = useParams<{ id: string }>();
  const detail = useQuery({ queryKey: ['public-case', id], queryFn: () => publicApi.detail(id).then((r) => r.data) });
  const hearings = useQuery({ queryKey: ['public-hearings', id], queryFn: () => publicApi.hearings(id).then((r) => r.data) });
  const orders = useQuery({ queryKey: ['public-orders', id], queryFn: () => publicApi.orders(id).then((r) => r.data) });
  const docs = useQuery({ queryKey: ['public-docs', id], queryFn: () => publicApi.documents(id).then((r) => r.data) });

  if (detail.isLoading) return <PublicShell><LoadingState /></PublicShell>;
  if (detail.error) return <PublicShell><ErrorState message="Case not found or not public" /></PublicShell>;

  const c = detail.data?.case;

  return (
    <PublicShell>
      <Link href="/guest/search" className="mb-4 inline-flex items-center gap-1 text-sm text-white/80 hover:text-white">
        <ArrowLeft size={16} /> Back to search
      </Link>

      <Card className="mb-5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold text-slate-900">{c.case_number}</h1>
          <StatusBadge status={c.status} />
        </div>
        <p className="mt-1 text-slate-600">{c.title}</p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <div><p className="text-xs text-slate-400">Case Type</p><p className="font-medium">{c.case_type}</p></div>
          <div><p className="text-xs text-slate-400">Court</p><p className="font-medium">{c.court_name || '—'}</p></div>
          <div><p className="text-xs text-slate-400">Filing Date</p><p className="font-medium">{formatDate(c.filing_date)}</p></div>
          <div><p className="text-xs text-slate-400">Next Hearing</p><p className="font-medium">{formatDate(c.next_hearing_date)}</p></div>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><CalendarDays size={16} /> Public Hearings</h3>
          {hearings.data?.hearings?.length === 0 && <p className="text-sm text-slate-400">No public hearings listed.</p>}
          <ul className="space-y-2 text-sm">
            {(hearings.data?.hearings || []).map((h: any) => (
              <li key={h.id} className="flex justify-between">
                <span className="text-slate-600">Hearing #{h.hearing_number} — {formatDate(h.date)}</span>
                <span className="text-slate-400">{h.status}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><ScrollText size={16} /> Public Orders</h3>
          {orders.data?.orders?.length === 0 && <p className="text-sm text-slate-400">No public orders published.</p>}
          <ul className="space-y-2 text-sm">
            {(orders.data?.orders || []).map((o: any) => (
              <li key={o.id} className="flex justify-between">
                <span className="text-slate-600">{o.title}</span>
                <span className="text-slate-400">{formatDate(o.date)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="mt-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><FileText size={16} /> Public Documents</h3>
        {docs.data?.documents?.length === 0 && <p className="text-sm text-slate-400">No public documents.</p>}
        <ul className="space-y-2 text-sm">
          {(docs.data?.documents || []).map((d: any) => (
            <li key={d.id} className="flex justify-between">
              <span className="text-slate-600">{d.file_name}</span>
              <span className="text-slate-400">{formatDate(d.uploaded_at)}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="mt-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><Scale size={16} /> Public Timeline</h3>
        {detail.data?.timeline?.length === 0 && <p className="text-sm text-slate-400">No public timeline events.</p>}
        <ol className="space-y-3">
          {(detail.data?.timeline || []).map((e: any, i: number) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="w-28 shrink-0 text-xs text-slate-400">{formatDate(e.date)}</span>
              <div>
                <p className="font-medium text-slate-700">{e.title}</p>
                {e.description ? <p className="text-slate-500">{e.description}</p> : null}
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <div className="mt-6 flex items-start gap-2 rounded-lg bg-slate-50 p-4 text-xs text-slate-500">
        <Info size={14} className="mt-0.5 shrink-0" />
        <p>Only public information about this case is displayed. Restricted documents, internal notes and private personal information are not available through the public interface.</p>
      </div>
    </PublicShell>
  );
}

function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-brand-800 px-6 py-3 text-white">
        <Link href="/guest/search" className="flex w-fit items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-white/20"><Scale size={16} /></div>
          <span className="text-sm font-bold">JCM Public Case Information</span>
        </Link>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-6">{children}</main>
    </div>
  );
}
