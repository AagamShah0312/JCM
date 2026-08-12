import React from 'react';
import { Link } from 'react-router-dom';
import { FiArrowRight } from 'react-icons/fi';
import { formatDisplayDate } from '../lib/date';

export default function CasesList({ cases, renderAction }) {
  const caseItems = Array.isArray(cases) ? cases : cases?.results || [];
  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300';
      case 'pending':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300';
      case 'closed':
        return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200';
      case 'appealed':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300';
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200';
    }
  };

  return (
    <div className="space-y-3">
      {caseItems.map((caseItem) => (
        <div
          key={caseItem.id}
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-500"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <Link to={`/cases/${caseItem.id}`} className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="truncate text-base font-semibold text-slate-900 dark:text-slate-100">
                  {caseItem.case_number}
                </h3>
                <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${getStatusColor(caseItem.status)}`}>
                  {caseItem.status}
                </span>
              </div>

              <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                {caseItem.title}
              </p>

              <div className="mt-3 grid gap-1 text-sm text-slate-600 dark:text-slate-400 sm:grid-cols-2">
                <p className="truncate">
                  <span className="font-medium text-slate-800 dark:text-slate-200">Plaintiff:</span> {caseItem.plaintiff_name}
                </p>
                <p className="truncate">
                  <span className="font-medium text-slate-800 dark:text-slate-200">Defendant:</span> {caseItem.defendant_name}
                </p>
              </div>

              {caseItem.next_hearing_date && (
                <p className="mt-3 text-sm text-blue-700 dark:text-blue-300">
                  Next hearing: {formatDisplayDate(caseItem.next_hearing_date)}
                </p>
              )}
            </Link>

            <div className="flex items-center justify-between gap-3 sm:justify-end">
              {renderAction ? renderAction(caseItem) : null}
              <Link
                to={`/cases/${caseItem.id}`}
                className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-700 dark:text-slate-300 dark:hover:border-blue-500 dark:hover:bg-blue-950/40 dark:hover:text-blue-300"
                aria-label={`Open ${caseItem.case_number}`}
              >
                <FiArrowRight />
              </Link>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
