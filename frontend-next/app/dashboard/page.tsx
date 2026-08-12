'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, homeForRole } from '@/lib/auth';

export default function DashboardRedirect() {
  const router = useRouter();
  const user = useAuth((s) => s.user);
  useEffect(() => {
    router.replace(homeForRole(user?.role));
  }, [user, router]);
  return null;
}
