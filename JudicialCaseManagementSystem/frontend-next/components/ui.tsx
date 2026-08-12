'use client';

import React from 'react';
import Link from 'next/link';
import clsx from 'clsx';
import type { Role } from '@/types';

/** Small, dependency-light UI primitives (shadcn-style but hand-rolled). */

export function Badge({ children, tone = 'slate' }: { children: React.ReactNode; tone?: 'slate' | 'green' | 'red' | 'amber' | 'blue' | 'violet' }) {
  const tones: Record<string, string> = {
    slate: 'bg-slate-100 text-slate-700 ring-slate-200',
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    red: 'bg-red-50 text-red-700 ring-red-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-200',
    blue: 'bg-blue-50 text-blue-700 ring-blue-200',
    violet: 'bg-violet-50 text-violet-700 ring-violet-200',
  };
  return (
    <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset', tones[tone])}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = (status || '').toUpperCase();
  const map: Record<string, { tone: 'slate' | 'green' | 'red' | 'amber' | 'blue' | 'violet'; label: string }> = {
    FILED: { tone: 'blue', label: 'Filed' },
    REGISTERED: { tone: 'blue', label: 'Registered' },
    PENDING: { tone: 'amber', label: 'Pending' },
    ACTIVE: { tone: 'green', label: 'Active' },
    ADJOURNED: { tone: 'amber', label: 'Adjourned' },
    RESERVED_FOR_ORDER: { tone: 'violet', label: 'Reserved for Order' },
    DISPOSED: { tone: 'slate', label: 'Disposed' },
    TRANSFERRED: { tone: 'violet', label: 'Transferred' },
    CLOSED: { tone: 'slate', label: 'Closed' },
    SCHEDULED: { tone: 'blue', label: 'Scheduled' },
    IN_PROGRESS: { tone: 'green', label: 'In Progress' },
    COMPLETED: { tone: 'green', label: 'Completed' },
    CANCELLED: { tone: 'red', label: 'Cancelled' },
    DRAFT: { tone: 'amber', label: 'Draft' },
    SIGNED: { tone: 'blue', label: 'Signed' },
    PUBLISHED: { tone: 'green', label: 'Published' },
    SUPERSEDED: { tone: 'slate', label: 'Superseded' },
  };
  const m = map[s] || { tone: 'slate' as const, label: status || '—' };
  return <Badge tone={m.tone}>{m.label}</Badge>;
}

export function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx('card p-5', className)}>{children}</div>;
}

export function StatCard({ label, value, icon }: { label: string; value: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <Card className="flex items-start justify-between">
      <div>
        <p className="text-sm text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      </div>
      {icon ? <div className="text-brand-500">{icon}</div> : null}
    </Card>
  );
}

export function SectionTitle({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-start justify-between">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {subtitle ? <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, message, action }: { title: string; message?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white py-16 text-center">
      <p className="text-base font-medium text-slate-700">{title}</p>
      {message ? <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-500">
      <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <p className="font-medium">Something went wrong</p>
      <p className="mt-1">{message}</p>
      {onRetry ? (
        <button className="btn-secondary mt-3" onClick={onRetry}>Try again</button>
      ) : null}
    </div>
  );
}

export function RoleBadge({ role }: { role: Role }) {
  const tone = role === 'admin' ? 'red' : role === 'judge' ? 'violet' : role === 'lawyer' ? 'blue' : 'slate';
  return <Badge tone={tone}>{role}</Badge>;
}

export function NavLink({ href, active, children }: { href: string; active?: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={clsx(
        'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition',
        active ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100'
      )}
    >
      {children}
    </Link>
  );
}

export function Breadcrumbs({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav className="mb-4 flex items-center gap-1 text-sm text-slate-500">
      {items.map((it, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span>/</span>}
          {it.href ? (
            <Link href={it.href} className="hover:text-brand-600">{it.label}</Link>
          ) : (
            <span className="text-slate-700">{it.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}
