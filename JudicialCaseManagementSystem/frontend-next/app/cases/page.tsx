'use client';

import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { Plus, Search } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { SectionTitle, Card, LoadingState, ErrorState, StatusBadge } from '@/components/ui';
import CaseTable from '@/components/CaseTable';
import { casesApi } from '@/lib/services';
import { useAuth } from '@/lib/auth';
import { formatDate } from '@/lib/utils';
import toast from 'react-hot-toast';

const STATUSES = ['ALL', 'FILED', 'REGISTERED', 'PENDING', 'ACTIVE', 'ADJOURNED', 'RESERVED_FOR_ORDER', 'DISPOSED', 'CLOSED'];

export default function CasesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('ALL');
  const [showCreate, setShowCreate] = useState(false);

  const { data: cases, isLoading, error } = useQuery({
    queryKey: ['cases'],
    queryFn: () => casesApi.list({ search: search || undefined, status: status === 'ALL' ? undefined : status }).then((r) => r.data),
  });

  const filtered = useMemo(() => {
    if (!cases) return [];
    const q = search.toLowerCase();
    return cases.filter((c) => !q || c.case_number.toLowerCase().includes(q) || c.title.toLowerCase().includes(q) || (c.plaintiff_name || '').toLowerCase().includes(q));
  }, [cases, search]);

  const createMutation = useMutation({
    mutationFn: (data: any) => casesApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cases'] }); setShowCreate(false); toast.success('Case created'); },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Create failed'),
  });

  const [form, setForm] = useState<any>({ case_number: '', title: '', case_type: 'Civil', filing_date: '', plaintiff_name: '', defendant_name: '', description: '' });
  const setF = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setForm((f: any) => ({ ...f, [k]: e.target.value }));

  if (isLoading) return <AppShell><LoadingState /></AppShell>;
  if (error) return <AppShell><ErrorState message="Could not load cases" /></AppShell>;

  return (
    <AppShell>
      <SectionTitle
        title="Cases"
        subtitle="Browse cases you are authorized to access"
        action={user?.role === 'admin' || user?.role === 'judge' ? (
          <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}><Plus size={16} /> New Case</button>
        ) : undefined}
      />

      {showCreate && (
        <Card className="mb-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Create New Case</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <div><label className="label">Case number *</label><input className="input" value={form.case_number} onChange={setF('case_number')} /></div>
            <div><label className="label">Title *</label><input className="input" value={form.title} onChange={setF('title')} /></div>
            <div><label className="label">Case type *</label>
              <select className="input" value={form.case_type} onChange={setF('case_type')}>
                {['Civil', 'Criminal', 'Corporate', 'Family', 'Constitutional', 'Other'].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div><label className="label">Filing date *</label><input type="date" className="input" value={form.filing_date} onChange={setF('filing_date')} /></div>
            <div><label className="label">Petitioner</label><input className="input" value={form.plaintiff_name} onChange={setF('plaintiff_name')} /></div>
            <div><label className="label">Respondent</label><input className="input" value={form.defendant_name} onChange={setF('defendant_name')} /></div>
            <div className="md:col-span-3"><label className="label">Description</label><textarea className="input" rows={2} value={form.description} onChange={setF('description')} /></div>
          </div>
          <div className="mt-3 flex gap-2">
            <button className="btn-primary" disabled={createMutation.isPending || !form.case_number || !form.title} onClick={() => createMutation.mutate(form)}>
              {createMutation.isPending ? 'Creating…' : 'Create'}
            </button>
            <button className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </Card>
      )}

      <Card className="mb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input pl-9" placeholder="Search case number, title, party…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="input sm:w-52" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => <option key={s} value={s}>{s === 'ALL' ? 'All statuses' : s}</option>)}
          </select>
        </div>
      </Card>

      <CaseTable cases={filtered} />
    </AppShell>
  );
}
