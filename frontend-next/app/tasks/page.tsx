'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, StatusBadge, EmptyState } from '@/components/ui';
import { tasksApi, casesApi } from '@/lib/services';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';
import { useState } from 'react';

export default function TasksPage() {
  const qc = useQueryClient();
  const tasks = useQuery({ queryKey: ['tasks'], queryFn: () => tasksApi.list().then((r) => r.data) });
  const cases = useQuery({ queryKey: ['cases-min'], queryFn: () => casesApi.list().then((r) => r.data) });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({ title: '', case: '', priority: 'NORMAL', due_date: '' });

  const createT = useMutation({
    mutationFn: (d: any) => tasksApi.create({ ...d, assigned_to: d.assigned_to || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tasks'] }); setShowForm(false); toast.success('Task created'); },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Failed'),
  });
  const completeT = useMutation({
    mutationFn: (id: string) => tasksApi.complete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tasks'] }); toast.success('Task completed'); },
  });

  return (
    <AppShell>
      <SectionTitle title="Tasks" subtitle="Work items across your cases" action={<button className="btn-primary" onClick={() => setShowForm(!showForm)}>+ New Task</button>} />
      {showForm && (
        <Card className="mb-4">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="md:col-span-2"><label className="label">Title *</label><input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div><label className="label">Case</label>
              <select className="input" value={form.case} onChange={(e) => setForm({ ...form, case: e.target.value })}>
                <option value="">— none —</option>
                {(cases.data || []).map((c) => <option key={c.id} value={c.id}>{c.case_number}</option>)}
              </select>
            </div>
            <div><label className="label">Due date</label><input type="date" className="input" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} /></div>
          </div>
          <button className="btn-primary mt-3" disabled={!form.title} onClick={() => createT.mutate(form)}>Create</button>
        </Card>
      )}
      {tasks.isLoading && <LoadingState />}
      {tasks.error && <ErrorState message="Could not load tasks" />}
      {tasks.data && tasks.data.length === 0 && <EmptyState title="No tasks" message="Create tasks to track work on cases." />}
      <div className="space-y-3">
        {tasks.data?.map((t) => (
          <Card key={t.id}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">{t.title}</p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {t.case ? <Link href={`/cases/${t.case}`} className="text-brand-600 hover:underline">case link</Link> : 'No case'} · Due {formatDate(t.due_date)} · {t.priority}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={t.status} />
                {t.status !== 'DONE' && <button className="btn-secondary text-xs" onClick={() => completeT.mutate(t.id)}>Done</button>}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
