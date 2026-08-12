'use client';

import { useQuery } from '@tanstack/react-query';
import { Users } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, RoleBadge } from '@/components/ui';
import api from '@/lib/api';

export default function UsersPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['users'], queryFn: () => api.get('/auth/users/').then((r) => r.data) });

  return (
    <AppShell>
      <SectionTitle title="Users" subtitle="Judges, lawyers, admins and staff" />
      {isLoading && <LoadingState />}
      {error && <ErrorState message="Could not load users" />}
      <Card>
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead>
              <tr><th>Name</th><th>Email</th><th>Role</th><th>Professional ID</th><th>Verified</th></tr>
            </thead>
            <tbody>
              {(data || []).map((u: any) => (
                <tr key={u.id}>
                  <td className="font-medium text-slate-800">{(u.first_name || '') + ' ' + (u.last_name || '')}</td>
                  <td>{u.email}</td>
                  <td><RoleBadge role={u.role} /></td>
                  <td>{u.professional_id || '—'}</td>
                  <td>{u.is_verified ? '✓' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </AppShell>
  );
}
