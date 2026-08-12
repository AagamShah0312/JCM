'use client';

import Link from 'next/link';
import type { Case } from '@/types';
import { StatusBadge } from './ui';
import { format } from '@/lib/utils';

export default function CaseTable({ cases, onStatusFilter }: { cases: Case[]; onStatusFilter?: (s: string) => void }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>Case No.</th>
              <th>Title</th>
              <th>Type</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Next Hearing</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td className="font-medium text-brand-600">
                  <Link href={`/cases/${c.id}`}>{c.case_number}</Link>
                </td>
                <td className="max-w-[240px] truncate">{c.title}</td>
                <td>{c.case_type}</td>
                <td><StatusBadge status={c.status} /></td>
                <td>{c.priority}</td>
                <td>{c.next_hearing_date ? format(c.next_hearing_date) : '—'}</td>
                <td className="text-right">
                  <Link href={`/cases/${c.id}`} className="text-sm font-medium text-brand-600 hover:underline">
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {cases.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">No cases found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
