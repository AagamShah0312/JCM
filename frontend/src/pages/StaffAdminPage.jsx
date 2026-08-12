import React, { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { FiUpload, FiRefreshCw } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';
import { useAuthStore } from '../context/authStore';

export default function StaffAdminPage() {
  const { user } = useAuthStore();
  const [users, setUsers] = useState([]);
  const [role, setRole] = useState('judge');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await authAPI.listUsers();
      setUsers(response.data.results || response.data || []);
    } catch (error) {
      toast.error('Unable to load staff');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  const handleImport = async (event) => {
    event.preventDefault();
    if (!file) {
      toast.error('Select a CSV file first');
      return;
    }
    try {
      const response = await authAPI.importStaffCSV(role, file);
      toast.success(`Imported ${response.data.created} new and ${response.data.updated} updated users`);
      setFile(null);
      loadUsers();
    } catch (error) {
      toast.error('CSV import failed');
    }
  };

  const updateRole = async (staff, nextRole) => {
    try {
      await authAPI.promoteDemote(staff.id, { role: nextRole, professional_id: staff.professional_id || '' });
      toast.success('Role updated');
      loadUsers();
    } catch (error) {
      toast.error('Role update failed');
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Staff Admin</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Import Judge.csv or Lawyer.csv and manage staff roles.</p>
      </header>

      <form onSubmit={handleImport} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <select value={role} onChange={(event) => setRole(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
            <option value="judge">Judge.csv</option>
            <option value="lawyer">Lawyer.csv</option>
          </select>
          <input type="file" accept=".csv" onChange={(event) => setFile(event.target.files?.[0] || null)} className="rounded-md border border-dashed border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200" />
          <button type="submit" className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <FiUpload /> Upload CSV
          </button>
        </div>
      </form>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-700">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">Users</h2>
          <button onClick={loadUsers} className="inline-flex items-center gap-2 text-sm text-blue-700 dark:text-blue-300"><FiRefreshCw /> Refresh</button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm dark:divide-slate-700">
            <thead className="bg-slate-50 dark:bg-slate-950">
              <tr>
                {['Name', 'Email', 'Staff ID', 'Role', 'Promote/Demote'].map((heading) => (
                  <th key={heading} className="px-5 py-3 text-left font-medium text-slate-600 dark:text-slate-300">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {loading ? (
                <tr><td className="px-5 py-6 text-slate-500" colSpan={5}>Loading staff...</td></tr>
              ) : users.map((staff) => (
                <tr key={staff.id}>
                  <td className="px-5 py-3 text-slate-900 dark:text-slate-100">{staff.first_name || staff.username}</td>
                  <td className="px-5 py-3 text-slate-600 dark:text-slate-300">{staff.email}</td>
                  <td className="px-5 py-3 text-slate-600 dark:text-slate-300">{staff.professional_id || 'N/A'}</td>
                  <td className="px-5 py-3 capitalize text-slate-600 dark:text-slate-300">{staff.role}</td>
                  <td className="px-5 py-3">
                    <select value={staff.role} onChange={(event) => updateRole(staff, event.target.value)} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                      <option value="admin">Admin</option>
                      <option value="judge">Judge</option>
                      <option value="lawyer">Lawyer</option>
                      <option value="guest">Guest</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
