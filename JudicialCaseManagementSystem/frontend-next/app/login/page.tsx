'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Scale } from 'lucide-react';
import { useAuth, homeForRole } from '@/lib/auth';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const router = useRouter();
  const { login, user } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const res = await login(email, password);
    setLoading(false);
    if (res.success) {
      toast.success('Logged in');
      const role = useAuth.getState().user?.role;
      router.push(homeForRole(role));
    } else {
      toast.error(res.error || 'Login failed');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-700 to-brand-900 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Scale size={26} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">JCM</h1>
          <p className="text-sm text-slate-500">Judicial Case Management System</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@example.com" required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          No account?{' '}
          <Link href="/register" className="font-medium text-brand-600 hover:underline">Register</Link>
        </p>
        <div className="mt-4 rounded-md bg-slate-50 p-3 text-xs text-slate-500">
          <p className="font-semibold text-slate-600">Demo accounts (seed data):</p>
          <p>Admin: admin@example.com / Aagam%1234</p>
          <p>Judge: pass.iloveben10@gmail.com / Aagam%1234</p>
          <p>Lawyer: aagam0312@gmail.com / Aagam%1234</p>
        </div>
      </div>
    </div>
  );
}
