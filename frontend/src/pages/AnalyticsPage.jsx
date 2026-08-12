import React, { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';
import { useAuthStore } from '../context/authStore';
import CasesList from '../components/CasesList';

export default function AnalyticsPage() {
  const { user } = useAuthStore();
  const [staff, setStaff] = useState([]);
  const [selectedId, setSelectedId] = useState(user?.id || '');
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    const loadStaff = async () => {
      try {
        const response = await authAPI.listUsers();
        const list = (response.data.results || response.data || []).filter((item) => ['judge', 'lawyer'].includes(item.role));
        setStaff(list);
        if (!selectedId && list.length) setSelectedId(list[0].id);
      } catch (error) {
        toast.error('Unable to load legal history');
      }
    };
    loadStaff();
  }, [selectedId]);

  const loadAnalytics = useCallback(async () => {
    if (!selectedId) return;
    try {
      const response = await authAPI.userAnalytics(selectedId);
      setAnalytics(response.data);
    } catch (error) {
      toast.error('Unable to load analytics');
    }
  }, [selectedId]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Legal History & Analytics</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">View past cases, outcomes recorded in notes, and win percentage.</p>
      </header>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <label className="block space-y-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Judge or Lawyer ID</span>
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
            {staff.map((item) => (
              <option key={item.id} value={item.id}>
                {item.professional_id || item.id} - {item.first_name || item.email} ({item.role})
              </option>
            ))}
          </select>
        </label>
      </section>

      {analytics && (
        <>
          <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
            {[
              ['Total Cases', analytics.total_cases],
              ['Closed Cases', analytics.closed_cases],
              ['Active Cases', analytics.active_cases],
              ['Win %', `${analytics.win_percentage}%`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
              </div>
            ))}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <h2 className="mb-4 font-semibold text-slate-900 dark:text-slate-100">Recent Legal History</h2>
            {analytics.recent_cases?.length ? <CasesList cases={analytics.recent_cases} /> : <p className="text-sm text-slate-500 dark:text-slate-400">No case history found.</p>}
          </section>
        </>
      )}
    </div>
  );
}
