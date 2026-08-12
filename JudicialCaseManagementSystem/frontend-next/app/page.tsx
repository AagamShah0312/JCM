'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth, homeForRole } from '@/lib/auth';

export default function HomePage() {
  const router = useRouter();
  const user = useAuth((s) => s.user);

  useEffect(() => {
    if (user) {
      router.replace(homeForRole(user.role));
    } else {
      router.replace('/login');
    }
  }, [user, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
    </div>
  );
}
