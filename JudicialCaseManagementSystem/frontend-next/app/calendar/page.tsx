'use client';

import { Suspense, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft, ChevronRight, CalendarDays, CheckSquare } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, Badge } from '@/components/ui';
import { analyticsApi } from '@/lib/services';

function startOfMonth(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}
function addDays(d: Date, n: number) {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
function iso(d: Date) {
  return d.toISOString().slice(0, 10);
}

function CalendarInner() {
  const searchParams = useSearchParams();
  const paramDate = searchParams.get('date');
  const [month, setMonth] = useState(() => startOfMonth(paramDate ? new Date(paramDate + 'T00:00:00') : new Date()));
  const [selectedDate, setSelectedDate] = useState<string | null>(paramDate || iso(new Date()));

  const start = iso(month);
  const endIso = iso(addDays(new Date(month.getFullYear(), month.getMonth() + 1, 0), 1));

  const { data, isLoading, error } = useQuery({
    queryKey: ['calendar', start, endIso],
    queryFn: () => analyticsApi.calendar(start, endIso).then((r) => r.data),
  });

  const events = useMemo(() => data?.events || [], [data]);

  const byDate = useMemo(() => {
    const map: Record<string, any[]> = {};
    events.forEach((e: any) => {
      (map[e.date] = map[e.date] || []).push(e);
    });
    return map;
  }, [events]);

  // Build month grid
  const cells = useMemo(() => {
    const first = startOfMonth(month);
    const gridStart = addDays(first, -first.getDay());
    return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i));
  }, [month]);

  const nav = (delta: number) => setMonth((m) => new Date(m.getFullYear(), m.getMonth() + delta, 1));

  const selectedEvents = (selectedDate && byDate[selectedDate]) || [];

  return (
    <AppShell>
      <SectionTitle title="Calendar" subtitle="Hearings, deadlines and tasks" />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">
              {month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
            </h3>
            <div className="flex gap-1">
              <button className="btn-secondary p-1.5" onClick={() => nav(-1)}><ChevronLeft size={16} /></button>
              <button className="btn-secondary px-2 py-1 text-xs" onClick={() => setMonth(startOfMonth(new Date()))}>Today</button>
              <button className="btn-secondary p-1.5" onClick={() => nav(1)}><ChevronRight size={16} /></button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-semibold uppercase text-slate-400">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => <div key={d}>{d}</div>)}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              const key = iso(d);
              const inMonth = d.getMonth() === month.getMonth();
              const isToday = key === iso(new Date());
              const isSelected = key === selectedDate;
              const dayEvents = byDate[key] || [];
              return (
                <button
                  key={i}
                  onClick={() => setSelectedDate(key)}
                  className={`flex min-h-[64px] flex-col items-center rounded-md border p-1 text-xs transition ${
                    isSelected ? 'border-brand-500 bg-brand-50' : isToday ? 'border-brand-300 bg-white' : 'border-slate-100 bg-white'
                  } ${inMonth ? '' : 'opacity-40'}`}
                >
                  <span className={`font-medium ${isToday ? 'text-brand-600' : 'text-slate-600'}`}>{d.getDate()}</span>
                  <div className="mt-1 w-full space-y-0.5">
                    {dayEvents.slice(0, 3).map((e: any, j: number) => (
                      <div key={j} className={`h-1 w-full rounded ${e.type === 'hearing' ? 'bg-brand-400' : 'bg-emerald-400'}`} title={e.title} />
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <CalendarDays size={16} /> {selectedDate ? new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long' }) : 'Select a date'}
          </h3>
          {selectedEvents.length === 0 && <p className="text-sm text-slate-400">No events on this date.</p>}
          <ul className="space-y-3">
            {selectedEvents.map((e: any) => (
              <li key={`${e.type}-${e.id}`} className="rounded-md border border-slate-100 bg-slate-50 p-3 text-sm">
                <div className="flex items-center gap-2">
                  {e.type === 'hearing' ? <CalendarDays size={14} className="text-brand-500" /> : <CheckSquare size={14} className="text-emerald-500" />}
                  <Badge tone={e.type === 'hearing' ? 'blue' : 'green'}>{e.type}</Badge>
                  <span className="ml-auto text-xs text-slate-400">{e.time || ''}</span>
                </div>
                {e.type === 'hearing' ? (
                  <Link href={`/cases/${e.case_id || ''}`} className="mt-1 block font-medium text-slate-800 hover:text-brand-600">
                    {e.title}
                  </Link>
                ) : (
                  <p className="mt-1 font-medium text-slate-800">{e.title}</p>
                )}
                {e.status && <p className="mt-0.5 text-xs text-slate-400">Status: {e.status}{e.priority ? ` · ${e.priority}` : ''}</p>}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}


// useSearchParams requires a Suspense boundary during static prerendering.
export default function CalendarPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" /></div>}>
      <CalendarInner />
    </Suspense>
  );
}
