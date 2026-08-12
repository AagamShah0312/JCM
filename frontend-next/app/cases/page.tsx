'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { SectionTitle, Card, LoadingState, ErrorState } from '@/components/ui';
import CaseTable from '@/components/CaseTable';
import { casesApi } from '@/lib/services';
import { useAuth } from '@/lib/auth';
import { caseCreateSchema, type CaseCreateForm } from '@/lib/schemas';
import toast from 'react-hot-toast';

const STATUSES = ['ALL', 'FILED', 'REGISTERED', 'PENDING', 'ACTIVE', 'ADJOURNED', 'RESERVED_FOR_ORDER', 'DISPOSED', 'CLOSED'];
const TYPES = ['ALL', 'Civil', 'Criminal', 'Corporate', 'Family', 'Constitutional', 'Other'];
const PAGE_SIZE = 10;

export default function CasesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('ALL');
  const [type, setType] = useState('ALL');
  const [priority, setPriority] = useState('ALL');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  // Server-side pagination + filters (spec §52: don't load thousands into the browser)
  const { data, isLoading, error } = useQuery({
    queryKey: ['cases', search, status, type, priority, page],
    queryFn: () =>
      casesApi.list({
        search: search || undefined,
        status: status === 'ALL' ? undefined : status,
        case_type: type === 'ALL' ? undefined : type,
        priority: priority === 'ALL' ? undefined : priority,
        page,
        page_size: PAGE_SIZE,
      }).then((r) => r.data),
  });

  const cases = Array.isArray(data) ? data : data?.results || [];
  const total = Array.isArray(data) ? cases.length : data?.count || cases.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const createForm = useForm<CaseCreateForm>({
    resolver: zodResolver(caseCreateSchema),
    defaultValues: { case_type: 'Civil', priority: 'NORMAL' },
  });

  const createMutation = useMutation({
    mutationFn: (d: CaseCreateForm) => casesApi.create(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cases'] });
      setShowCreate(false);
      createForm.reset();
      toast.success('Case created');
    },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Create failed'),
  });

  const onSubmit = (values: CaseCreateForm) => createMutation.mutate(values);
  const createErrors = createForm.formState.errors;

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
          <form onSubmit={createForm.handleSubmit(onSubmit)} noValidate>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="label" htmlFor="cc-case_number">Case number *</label>
                <input id="cc-case_number" className="input" aria-invalid={!!createErrors.case_number} {...createForm.register('case_number')} />
                {createErrors.case_number && <p className="mt-1 text-xs text-red-600">{createErrors.case_number.message}</p>}
              </div>
              <div>
                <label className="label" htmlFor="cc-cnr">CNR number</label>
                <input id="cc-cnr" className="input" {...createForm.register('cnr_number')} />
              </div>
              <div>
                <label className="label" htmlFor="cc-title">Title *</label>
                <input id="cc-title" className="input" aria-invalid={!!createErrors.title} {...createForm.register('title')} />
                {createErrors.title && <p className="mt-1 text-xs text-red-600">{createErrors.title.message}</p>}
              </div>
              <div>
                <label className="label" htmlFor="cc-type">Case type *</label>
                <select id="cc-type" className="input" {...createForm.register('case_type')}>
                  {['Civil', 'Criminal', 'Corporate', 'Family', 'Constitutional', 'Other'].map((t) => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="cc-priority">Priority</label>
                <select id="cc-priority" className="input" {...createForm.register('priority')}>
                  {['URGENT', 'HIGH', 'NORMAL', 'LOW'].map((p) => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="cc-filing">Filing date *</label>
                <input id="cc-filing" type="date" className="input" aria-invalid={!!createErrors.filing_date} {...createForm.register('filing_date')} />
                {createErrors.filing_date && <p className="mt-1 text-xs text-red-600">{createErrors.filing_date.message}</p>}
              </div>
              <div><label className="label" htmlFor="cc-plaintiff">Petitioner</label><input id="cc-plaintiff" className="input" {...createForm.register('plaintiff_name')} /></div>
              <div><label className="label" htmlFor="cc-defendant">Respondent</label><input id="cc-defendant" className="input" {...createForm.register('defendant_name')} /></div>
              <div className="md:col-span-3">
                <label className="label" htmlFor="cc-desc">Description</label>
                <textarea id="cc-desc" className="input" rows={2} {...createForm.register('description')} />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating…' : 'Create'}
              </button>
              <button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </form>
        </Card>
      )}

      <Card className="mb-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input pl-9" aria-label="Search cases" placeholder="Search case number, title, party…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
          </div>
          <div className="flex flex-wrap gap-2">
            <select className="input sm:w-44" aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
              {STATUSES.map((s) => <option key={s} value={s}>{s === 'ALL' ? 'All statuses' : s}</option>)}
            </select>
            <select className="input sm:w-40" aria-label="Filter by type" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }}>
              {TYPES.map((t) => <option key={t} value={t}>{t === 'ALL' ? 'All types' : t}</option>)}
            </select>
            <select className="input sm:w-36" aria-label="Filter by priority" value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }}>
              {['ALL', 'URGENT', 'HIGH', 'NORMAL', 'LOW'].map((p) => <option key={p} value={p}>{p === 'ALL' ? 'All priorities' : p}</option>)}
            </select>
          </div>
        </div>
      </Card>

      <CaseTable cases={cases} />

      {/* Server-side pagination */}
      <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
        <span>Showing {cases.length} of {total} · page {page}/{totalPages}</span>
        <div className="flex gap-2">
          <button className="btn-secondary p-1.5" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} aria-label="Previous page">
            <ChevronLeft size={16} />
          </button>
          <button className="btn-secondary p-1.5" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} aria-label="Next page">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </AppShell>
  );
}
