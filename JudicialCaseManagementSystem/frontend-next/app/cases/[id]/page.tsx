'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import {
  LayoutDashboard, History, CalendarDays, FileText, ScrollText, Users, CheckSquare, Bot, Upload, Download,
} from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, StatusBadge, Badge, EmptyState } from '@/components/ui';
import { casesApi, hearingsApi, ordersApi, documentsApi, tasksApi, analyticsApi } from '@/lib/services';
import AIAssistantPanel from '@/components/AIAssistantPanel';
import { formatDate, formatDateTime, timeAgo } from '@/lib/utils';
import toast from 'react-hot-toast';
import { useAuth } from '@/lib/auth';
import type { Hearing, CaseDocument, Order, Task } from '@/types';

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'timeline', label: 'Timeline', icon: History },
  { id: 'hearings', label: 'Hearings', icon: CalendarDays },
  { id: 'proceedings', label: 'Proceedings', icon: ScrollText },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'orders', label: 'Orders', icon: ScrollText },
  { id: 'parties', label: 'Parties', icon: Users },
  { id: 'tasks', label: 'Tasks', icon: CheckSquare },
  { id: 'ai', label: 'AI Assistant', icon: Bot },
];

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState('overview');

  const caseQ = useQuery({ queryKey: ['case', id], queryFn: () => casesApi.retrieve(id).then((r) => r.data) });
  const hearingsQ = useQuery({ queryKey: ['case-hearings', id], queryFn: () => hearingsApi.list({ case: id }).then((r) => r.data) });
  const docsQ = useQuery({ queryKey: ['case-docs', id], queryFn: () => documentsApi.list({ case: id }).then((r) => r.data) });
  const ordersQ = useQuery({ queryKey: ['case-orders', id], queryFn: () => ordersApi.list({ case: id }).then((r) => r.data) });
  const tasksQ = useQuery({ queryKey: ['case-tasks', id], queryFn: () => tasksApi.list({ case: id }).then((r) => r.data) });
  const timelineQ = useQuery({ queryKey: ['case-timeline', id], queryFn: () => casesApi.timeline(id).then((r) => r.data) });
  const healthQ = useQuery({ queryKey: ['case-health', id], queryFn: () => analyticsApi.caseHealth(id).then((r) => r.data), enabled: !!user });

  const caseData = caseQ.data;
  const canEdit = user?.role === 'admin' || user?.role === 'judge';

  if (caseQ.isLoading) return <AppShell><LoadingState /></AppShell>;
  if (caseQ.error) return <AppShell><ErrorState message="Could not load case" /></AppShell>;
  if (!caseData) return <AppShell><EmptyState title="Case not found" /></AppShell>;

  return (
    <AppShell>
      {/* Persistent case header (spec §77) */}
      <Card className="mb-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900">{caseData.case_number}</h1>
              <StatusBadge status={caseData.status} />
              <Badge tone={caseData.priority === 'URGENT' ? 'red' : caseData.priority === 'HIGH' ? 'amber' : 'blue'}>{caseData.priority}</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-600">{caseData.title}</p>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
              <span>Court: <b>{caseData.court_name || '—'}</b></span>
              <span>Type: <b>{caseData.case_type}</b></span>
              <span>Judge: <b>{caseData.judge_name || '—'}</b></span>
              <span>Next hearing: <b>{formatDate(caseData.next_hearing_date)}</b></span>
              <span>Filed: <b>{formatDate(caseData.filing_date)}</b></span>
            </div>
          </div>
          {healthQ.data && healthQ.data.warnings?.length > 0 && (
            <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-700">
              <p className="mb-1 font-semibold">Case health warnings:</p>
              <ul className="list-inside list-disc space-y-0.5">
                {healthQ.data.warnings.slice(0, 3).map((w: any, i: number) => <li key={i}>{w.message}</li>)}
              </ul>
            </div>
          )}
        </div>
      </Card>

      {/* Tabs */}
      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button key={t.id}
              className={`flex items-center gap-1.5 rounded-t-md px-3 py-2 text-sm font-medium ${active ? 'border-b-2 border-brand-600 text-brand-700' : 'text-slate-500 hover:text-slate-800'}`}
              onClick={() => setTab(t.id)}>
              <Icon size={15} /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'overview' && <OverviewTab caseId={id} caseData={caseData} health={healthQ.data} />}
      {tab === 'timeline' && <TimelineTab events={timelineQ.data || []} loading={timelineQ.isLoading} />}
      {tab === 'hearings' && <HearingsTab caseId={id} hearings={hearingsQ.data || []} loading={hearingsQ.isLoading} canEdit={canEdit} />}
      {tab === 'proceedings' && <ProceedingsTab hearings={hearingsQ.data || []} loading={hearingsQ.isLoading} />}
      {tab === 'documents' && <DocumentsTab caseId={id} docs={docsQ.data || []} loading={docsQ.isLoading} canEdit={canEdit} />}
      {tab === 'orders' && <OrdersTab caseId={id} orders={ordersQ.data || []} loading={ordersQ.isLoading} canEdit={canEdit} />}
      {tab === 'parties' && <PartiesTab caseId={id} canEdit={canEdit} />}
      {tab === 'tasks' && <TasksTab caseId={id} tasks={tasksQ.data || []} loading={tasksQ.isLoading} />}
      {tab === 'ai' && <AIAssistantPanel caseId={id} />}
    </AppShell>
  );
}

/* ---------------- Tabs ---------------- */

function OverviewTab({ caseData, health }: { caseId: string; caseData: any; health?: any }) {
  const items: [string, any][] = [
    ['Case Number', caseData.case_number],
    ['CNR Number', caseData.cnr_number || '—'],
    ['Case Type', caseData.case_type],
    ['Status', caseData.status],
    ['Priority', caseData.priority],
    ['Court', caseData.court_name || '—'],
    ['Filing Date', formatDate(caseData.filing_date)],
    ['Registration Date', formatDate(caseData.registration_date)],
    ['Next Hearing', formatDate(caseData.next_hearing_date)],
    ['Petitioner', caseData.plaintiff_name || '—'],
    ['Respondent', caseData.defendant_name || '—'],
    ['Judge', caseData.judge_name || '—'],
    ['Subject', caseData.subject || '—'],
    ['Category', caseData.category || '—'],
    ['Disposal Date', formatDate(caseData.disposal_date)],
    ['Disposal Reason', caseData.disposal_reason || '—'],
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Description</h3>
        <p className="whitespace-pre-wrap text-sm text-slate-600">{caseData.description || 'No description provided.'}</p>
      </Card>
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Case Details</h3>
        <dl className="space-y-2 text-sm">
          {items.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <dt className="text-slate-500">{k}</dt>
              <dd className="text-right font-medium text-slate-800">{v}</dd>
            </div>
          ))}
        </dl>
        {health && (
          <div className="mt-4 border-t border-slate-100 pt-3">
            <h4 className="mb-2 text-xs font-semibold uppercase text-slate-400">Case Health</h4>
            <dl className="space-y-1 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Age</dt><dd className="font-medium">{health.case_age_days} days</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Hearings</dt><dd className="font-medium">{health.hearings_total}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Adjournments</dt><dd className="font-medium">{health.adjournments}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Documents</dt><dd className="font-medium">{health.documents_count}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Orders</dt><dd className="font-medium">{health.orders_count}</dd></div>
            </dl>
          </div>
        )}
      </Card>
    </div>
  );
}

function TimelineTab({ events, loading }: { events: any[]; loading: boolean }) {
  if (loading) return <LoadingState />;
  if (events.length === 0) return <EmptyState title="No timeline events yet" message="Events are generated from actual backend actions (hearings, orders, documents, status changes)." />;
  const sorted = [...events].sort((a, b) => (b.event_date || '').localeCompare(a.event_date || ''));
  return (
    <Card>
      <ol className="relative space-y-4 border-l-2 border-slate-200 pl-5">
        {sorted.map((e) => (
          <li key={e.id} className="relative">
            <span className="absolute -left-[26px] top-1 h-3 w-3 rounded-full border-2 border-white bg-brand-500 ring-2 ring-brand-100" />
            <p className="text-sm font-medium text-slate-800">{e.title}</p>
            <p className="text-xs text-slate-400">{formatDate(e.event_date)} {e.related_entity ? `· ${e.related_entity}` : ''}</p>
            {e.description ? <p className="mt-1 text-sm text-slate-600">{e.description}</p> : null}
          </li>
        ))}
      </ol>
    </Card>
  );
}

function HearingsTab({ caseId, hearings, loading, canEdit }: { caseId: string; hearings: Hearing[]; loading: boolean; canEdit: boolean }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({ date: '', hearing_type: 'FIRST', purpose: '' });
  const createH = useMutation({
    mutationFn: (d: any) => hearingsApi.create({ case: caseId, ...d }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-hearings'] }); setShowForm(false); toast.success('Hearing scheduled'); },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Failed'),
  });
  const reschedule = useMutation({
    mutationFn: ({ hid, d }: any) => hearingsApi.reschedule(hid, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-hearings'] }); toast.success('Hearing rescheduled (audited)'); },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Failed'),
  });
  const complete = useMutation({
    mutationFn: ({ hid, d }: any) => hearingsApi.complete(hid, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-hearings'] }); toast.success('Hearing completed / proceedings recorded'); },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Failed'),
  });

  if (loading) return <LoadingState />;
  const sorted = [...hearings].sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-4">
      {canEdit && (
        <div className="flex justify-end">
          <button className="btn-primary" onClick={() => setShowForm(!showForm)}>+ Schedule Hearing</button>
        </div>
      )}
      {showForm && (
        <Card>
          <div className="grid gap-3 md:grid-cols-4">
            <div><label className="label">Date *</label><input type="date" className="input" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></div>
            <div><label className="label">Type</label>
              <select className="input" value={form.hearing_type} onChange={(e) => setForm({ ...form, hearing_type: e.target.value })}>
                {['FIRST', 'ARGUMENTS', 'EVIDENCE', 'ORDER', 'INTERIM', 'ADJOURNMENT', 'OTHER'].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div className="md:col-span-2"><label className="label">Purpose</label><input className="input" value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} /></div>
          </div>
          <button className="btn-primary mt-3" disabled={!form.date || createH.isPending} onClick={() => createH.mutate(form)}>
            {createH.isPending ? 'Scheduling…' : 'Schedule'}
          </button>
        </Card>
      )}

      {sorted.length === 0 && <EmptyState title="No hearings yet" message="Hearings scheduled for this case will appear here." />}
      <div className="grid gap-4 lg:grid-cols-2">
        {sorted.map((h) => (
          <Card key={h.id}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">Hearing #{h.hearing_number} — {formatDate(h.date)}</p>
                <p className="text-xs text-slate-400">{h.hearing_type} {h.purpose ? `· ${h.purpose}` : ''}</p>
              </div>
              <StatusBadge status={h.status} />
            </div>
            {h.adjournment_reason && <p className="mt-2 text-xs text-amber-600">Adjourned: {h.adjournment_reason}</p>}
            {h.next_hearing_date && <p className="mt-1 text-xs text-slate-500">Next: {formatDate(h.next_hearing_date)}</p>}

            {canEdit && h.status === 'SCHEDULED' && (
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn-secondary text-xs" onClick={() => {
                  const nd = prompt('New date (YYYY-MM-DD):', h.date);
                  if (nd) reschedule.mutate({ hid: h.id, d: { new_date: nd } });
                }}>Reschedule</button>
                <button className="btn-secondary text-xs" onClick={() => {
                  const summary = prompt('Proceedings summary:');
                  if (summary !== null) complete.mutate({ hid: h.id, d: { summary } });
                }}>Complete + Record</button>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function ProceedingsTab({ hearings, loading }: { hearings: Hearing[]; loading: boolean }) {
  if (loading) return <LoadingState />;
  const procs = hearings.flatMap((h) => (h.proceedings || []).map((p) => ({ ...p, hearing: h })));
  if (procs.length === 0) return <EmptyState title="No proceedings recorded" message="Proceedings from completed hearings will appear here." />;
  return (
    <div className="space-y-4">
      {procs.map((p) => (
        <Card key={p.id}>
          <p className="text-sm font-semibold text-slate-800">Hearing #{p.hearing.hearing_number} — {formatDate(p.hearing.date)}</p>
          {p.summary && <p className="mt-2 text-sm text-slate-600">{p.summary}</p>}
          {p.directions && <p className="mt-1 text-sm text-slate-600"><b>Directions:</b> {p.directions}</p>}
          {p.next_action && <p className="mt-1 text-sm text-slate-600"><b>Next action:</b> {p.next_action}</p>}
        </Card>
      ))}
    </div>
  );
}

function DocumentsTab({ caseId, docs, loading, canEdit }: { caseId: string; docs: CaseDocument[]; loading: boolean; canEdit: boolean }) {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const upload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const arr = Array.from(files);
      await documentsApi.upload(caseId, arr, { document_type: 'other' });
      qc.invalidateQueries({ queryKey: ['case-docs'] });
      toast.success(`${arr.length} document(s) uploaded; processing started`);
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };
  const download = async (d: CaseDocument) => {
    try {
      const r = await documentsApi.download(d.id);
      window.open(r.data.download_url, '_blank');
    } catch (e: any) {
      toast.error(e?.response?.data?.error?.message || 'Not allowed');
    }
  };

  if (loading) return <LoadingState />;
  return (
    <div className="space-y-4">
      {canEdit && (
        <div className="flex items-center gap-2">
          <label className="btn-primary cursor-pointer">
            <Upload size={16} /> {uploading ? 'Uploading…' : 'Upload Documents'}
            <input type="file" multiple className="hidden" onChange={(e) => upload(e.target.files)} disabled={uploading} />
          </label>
        </div>
      )}
      {docs.length === 0 && <EmptyState title="No documents" message="Uploaded documents (PDF, DOCX, images, text) are processed for search and the AI assistant." />}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {docs.map((d) => (
          <Card key={d.id}>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-800">{d.file_name}</p>
                <p className="text-xs text-slate-400">{d.document_type} · {(d.file_size / 1024).toFixed(1)} KB</p>
              </div>
              <Badge tone={d.processing_state === 'PROCESSED' || d.processing_state === 'OCR_COMPLETED' ? 'green' : d.processing_state === 'FAILED' ? 'red' : 'amber'}>
                {d.processing_state}
              </Badge>
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs">
              <Badge tone={d.visibility === 'PUBLIC' ? 'green' : 'slate'}>{d.visibility}</Badge>
              <button className="ml-auto text-brand-600 hover:underline" onClick={() => download(d)}><Download size={14} className="mr-1 inline" />Download</button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function OrdersTab({ caseId, orders, loading, canEdit }: { caseId: string; orders: Order[]; loading: boolean; canEdit: boolean }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({ title: '', order_type: 'INTERIM', date: new Date().toISOString().slice(0, 10), summary: '' });
  const createO = useMutation({
    mutationFn: (d: any) => ordersApi.create({ case: caseId, ...d }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-orders'] }); setShowForm(false); toast.success('Order created (draft)'); },
    onError: (e: any) => toast.error(e?.response?.data?.error?.message || 'Failed'),
  });
  const publishO = useMutation({
    mutationFn: (oid: string) => ordersApi.publish(oid),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-orders'] }); toast.success('Order published'); },
  });

  if (loading) return <LoadingState />;
  return (
    <div className="space-y-4">
      {canEdit && (
        <div className="flex justify-end">
          <button className="btn-primary" onClick={() => setShowForm(!showForm)}>+ Create Order</button>
        </div>
      )}
      {showForm && (
        <Card>
          <div className="grid gap-3 md:grid-cols-3">
            <div><label className="label">Title *</label><input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div><label className="label">Type</label>
              <select className="input" value={form.order_type} onChange={(e) => setForm({ ...form, order_type: e.target.value })}>
                {['INTERIM', 'FINAL', 'JUDGMENT', 'DIRECTION', 'ADJOURNMENT', 'OTHER'].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div><label className="label">Date</label><input type="date" className="input" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></div>
            <div className="md:col-span-3"><label className="label">Summary</label><textarea className="input" rows={2} value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} /></div>
          </div>
          <button className="btn-primary mt-3" disabled={!form.title || createO.isPending} onClick={() => createO.mutate(form)}>Create Draft</button>
        </Card>
      )}
      {orders.length === 0 && <EmptyState title="No orders" message="Orders are separate from generic documents." />}
      <div className="space-y-3">
        {orders.map((o) => (
          <Card key={o.id}>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">{o.title}</p>
                <p className="text-xs text-slate-400">{o.order_type} · {formatDate(o.date)} · v{(o.versions || []).length || 1}</p>
                {o.summary && <p className="mt-1 text-sm text-slate-600">{o.summary}</p>}
              </div>
              <div className="flex flex-col items-end gap-1">
                <StatusBadge status={o.status} />
                {canEdit && o.status === 'DRAFT' && (
                  <button className="btn-secondary mt-1 text-xs" onClick={() => publishO.mutate(o.id)}>Publish</button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function PartiesTab({ caseId, canEdit }: { caseId: string; canEdit: boolean }) {
  const partiesQ = useQuery({ queryKey: ['case-parties', caseId], queryFn: () => casesApi.parties(caseId).then((r) => r.data) });
  const qc = useQueryClient();
  const [form, setForm] = useState<any>({ name: '', party_type: 'petitioner' });
  const addP = useMutation({
    mutationFn: (d: any) => casesApi.addParty(caseId, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-parties'] }); setForm({ name: '', party_type: 'petitioner' }); toast.success('Party added'); },
  });
  const parties = partiesQ.data || [];
  return (
    <div className="space-y-4">
      {canEdit && (
        <Card>
          <div className="flex gap-3">
            <input className="input" placeholder="Party name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <select className="input sm:w-48" value={form.party_type} onChange={(e) => setForm({ ...form, party_type: e.target.value })}>
              {['petitioner', 'respondent', 'applicant', 'opponent', 'intervenor', 'third_party'].map((t) => <option key={t}>{t}</option>)}
            </select>
            <button className="btn-primary" disabled={!form.name || addP.isPending} onClick={() => addP.mutate(form)}>Add</button>
          </div>
        </Card>
      )}
      {parties.length === 0 && <EmptyState title="No parties" message="Add petitioners and respondents for this case." />}
      <div className="grid gap-3 md:grid-cols-2">
        {parties.map((p: any) => (
          <Card key={p.id}>
            <div className="flex justify-between">
              <p className="text-sm font-semibold text-slate-800">{p.name}</p>
              <Badge tone={p.party_type === 'petitioner' ? 'blue' : p.party_type === 'respondent' ? 'amber' : 'slate'}>{p.party_type}</Badge>
            </div>
            <p className="text-xs text-slate-400">{p.party_kind}{p.representation ? ` · ${p.representation}` : ''}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

function TasksTab({ caseId, tasks, loading }: { caseId: string; tasks: Task[]; loading: boolean }) {
  const qc = useQueryClient();
  const completeT = useMutation({
    mutationFn: (tid: string) => tasksApi.complete(tid),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-tasks'] }); toast.success('Task completed'); },
  });
  if (loading) return <LoadingState />;
  if (tasks.length === 0) return <EmptyState title="No tasks" message="Tasks for this case will appear here." />;
  return (
    <div className="space-y-3">
      {tasks.map((t) => (
        <Card key={t.id}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-800">{t.title}</p>
              {t.description && <p className="text-sm text-slate-600">{t.description}</p>}
              <p className="mt-1 text-xs text-slate-400">Due: {formatDate(t.due_date)} · {t.priority}</p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <StatusBadge status={t.status} />
              {t.status !== 'DONE' && (
                <button className="btn-secondary mt-1 text-xs" onClick={() => completeT.mutate(t.id)}>Mark done</button>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
