'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search, Scale, Info } from 'lucide-react';
import { Card, StatusBadge, EmptyState, LoadingState } from '@/components/ui';
import { publicApi } from '@/lib/services';
import { formatDate } from '@/lib/utils';
import { useAuth } from '@/lib/auth';

export default function GuestSearchPage() {
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const [caseType, setCaseType] = useState('');
  const [court, setCourt] = useState('');
  const [status, setStatus] = useState('');
  const [submitted, setSubmitted] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['public-search', submitted, caseType, court, status],
    queryFn: () => publicApi.search({
      search: submitted || undefined,
      case_type: caseType || undefined,
      court: court || undefined,
      status: status || undefined,
    }).then((r) => r.data),
    enabled: Boolean(submitted || caseType || court || status),
  });

  const runSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(search.trim());
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-700 to-brand-900">
      <header className="flex items-center justify-between px-6 py-4 text-white">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-white/20"><Scale size={18} /></div>
          <span className="font-bold">JCM Public Case Search</span>
        </div>
        {user ? (
          <Link href={user.role === 'admin' ? '/admin' : user.role === 'judge' ? '/judge' : user.role === 'lawyer' ? '/lawyer' : '/login'} className="text-sm text-white/80 hover:text-white">
            Back to dashboard →
          </Link>
        ) : (
          <Link href="/login" className="rounded-md bg-white/20 px-3 py-1.5 text-sm hover:bg-white/30">Sign in</Link>
        )}
      </header>

      <main className="mx-auto max-w-4xl px-4 pb-16">
        <div className="py-10 text-center text-white">
          <h1 className="text-3xl font-bold">Search Public Case Information</h1>
          <p className="mt-2 text-sm text-white/70">Find cases by number, CNR, title, or party name. Only public information is shown.</p>
        </div>

        <form onSubmit={runSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="w-full rounded-lg border-0 bg-white py-3 pl-10 pr-4 text-slate-900 shadow-lg outline-none"
              placeholder="Case number, CNR, title, party…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button className="rounded-lg bg-white px-6 font-medium text-brand-700 shadow-lg hover:bg-slate-100">Search</button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          <select
            className="rounded-lg border-0 bg-white/95 px-3 py-2 text-sm text-slate-700 shadow outline-none"
            value={caseType}
            onChange={(e) => setCaseType(e.target.value)}
          >
            <option value="">All case types</option>
            {['Civil', 'Criminal', 'Corporate', 'Family', 'Constitutional', 'Other'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <input
            className="rounded-lg border-0 bg-white/95 px-3 py-2 text-sm text-slate-700 shadow outline-none"
            placeholder="Court name…"
            value={court}
            onChange={(e) => setCourt(e.target.value)}
          />
          <select
            className="rounded-lg border-0 bg-white/95 px-3 py-2 text-sm text-slate-700 shadow outline-none"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            {['FILED', 'REGISTERED', 'PENDING', 'ACTIVE', 'ADJOURNED', 'RESERVED_FOR_ORDER', 'DISPOSED', 'CLOSED'].map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        <div className="mt-8">
          {isLoading && <LoadingState label="Searching public records…" />}
          {error && <div className="rounded-lg bg-white/10 p-4 text-sm text-white/80">Search failed. Try again.</div>}
          {data && data.count === 0 && <EmptyState title="No public cases found" message="Try a different case number or party name." />}
          <div className="space-y-3">
            {data?.results?.map((c: any) => (
              <Link key={c.id} href={`/guest/cases/${c.id}`} className="block rounded-lg bg-white p-4 shadow transition hover:shadow-md">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-slate-800">{c.case_number} <span className="font-normal text-slate-500">— {c.title}</span></p>
                    <p className="mt-1 text-xs text-slate-500">
                      {c.case_type} · {c.court_name || 'Court'} · Filed {formatDate(c.filing_date)}
                    </p>
                  </div>
                  <StatusBadge status={c.status} />
                </div>
                {c.next_hearing_date && <p className="mt-2 text-xs text-slate-500">Next hearing: {formatDate(c.next_hearing_date)}</p>}
              </Link>
            ))}
          </div>
        </div>

        <div className="mt-10 flex items-start gap-2 rounded-lg bg-white/10 p-4 text-xs text-white/70">
          <Info size={14} className="mt-0.5 shrink-0" />
          <p>This public interface only shows information explicitly marked public (case number, type, court, status, public hearings/orders/documents). Restricted documents, internal notes and non-public personal information are never exposed.</p>
        </div>
      </main>
    </div>
  );
}
