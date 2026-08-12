'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import type { Role } from '@/types';

/** Client-side route guard (UX only — backend remains the authority). */
export function useRequireAuth(roles?: Role[]) {
  const router = useRouter();
  const user = useAuth((s) => s.user);
  const hydrated = useAuth((s) => s.hydrated);

  useEffect(() => {
    if (!hydrated) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (roles && !roles.includes(user.role)) {
      router.replace('/dashboard');
    }
  }, [hydrated, user, roles, router]);

  return { user, ready: hydrated && !!user && (!roles || roles.includes(user.role)) };
}
