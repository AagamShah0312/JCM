'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, LoadingState, ErrorState, EmptyState, Badge } from '@/components/ui';
import { notificationsApi } from '@/lib/services';
import { timeAgo } from '@/lib/utils';
import toast from 'react-hot-toast';

export default function NotificationsPage() {
  const qc = useQueryClient();
  const notifs = useQuery({ queryKey: ['notifications'], queryFn: () => notificationsApi.list().then((r) => r.data) });
  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAll(),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['notifications'] }); toast.success('All marked as read'); },
  });
  const markOne = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  return (
    <AppShell>
      <SectionTitle title="Notifications" subtitle="Updates on your cases" action={<button className="btn-secondary" onClick={() => markAll.mutate()}>Mark all read</button>} />
      {notifs.isLoading && <LoadingState />}
      {notifs.error && <ErrorState message="Could not load notifications" />}
      {notifs.data && notifs.data.length === 0 && <EmptyState title="No notifications" />}
      <div className="space-y-3">
        {notifs.data?.map((n) => (
          <Card key={n.id} className={n.is_read ? 'opacity-60' : ''}>
            <div className="flex items-start justify-between gap-3" onClick={() => !n.is_read && markOne.mutate(n.id)}>
              <div className="cursor-pointer">
                <p className="text-sm font-semibold text-slate-800">{n.title}</p>
                <p className="mt-0.5 text-sm text-slate-600">{n.message}</p>
                <p className="mt-1 text-xs text-slate-400">{timeAgo(n.created_at)}</p>
              </div>
              {!n.is_read && <Badge tone="blue">new</Badge>}
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
