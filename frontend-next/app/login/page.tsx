'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Scale, ShieldCheck, ArrowLeft } from 'lucide-react';
import { useAuth, homeForRole } from '@/lib/auth';
import { loginSchema, type LoginForm } from '@/lib/schemas';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const router = useRouter();
  const { login, loginMfa } = useAuth();
  const [loading, setLoading] = useState(false);
  const [mfaStep, setMfaStep] = useState<{ token: string; user: any } | null>(null);
  const [code, setCode] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (values: LoginForm) => {
    setLoading(true);
    const res = await login(values.email, values.password);
    setLoading(false);
    if (res.success) {
      toast.success('Logged in');
      router.push(homeForRole(useAuth.getState().user?.role));
    } else if (res.mfaRequired) {
      setMfaStep({ token: res.mfaToken || '', user: res.mfaUser });
      toast('Two-factor code required', { icon: '🔐' });
    } else {
      toast.error(res.error || 'Login failed');
    }
  };

  const onSubmitMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaStep) return;
    setLoading(true);
    const res = await loginMfa(mfaStep.token, code);
    setLoading(false);
    if (res.success) {
      toast.success('Logged in');
      router.push(homeForRole(useAuth.getState().user?.role));
    } else {
      toast.error(res.error || 'Invalid code');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-700 to-brand-900 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-2xl">
        {!mfaStep ? (
          <>
            <div className="mb-6 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-brand-600 text-white">
                <Scale size={26} />
              </div>
              <h1 className="text-2xl font-bold text-slate-900">JCM</h1>
              <p className="text-sm text-slate-500">Judicial Case Management System</p>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <div>
                <label className="label" htmlFor="login-email">Email</label>
                <input id="login-email" className="input" type="email" placeholder="admin@example.com"
                  aria-invalid={!!errors.email} {...register('email')} />
                {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
              </div>
              <div>
                <label className="label" htmlFor="login-password">Password</label>
                <input id="login-password" className="input" type="password" placeholder="••••••••"
                  aria-invalid={!!errors.password} {...register('password')} />
                {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>}
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
              <p>Judge: judge.mehta@example.com / Aagam%1234</p>
              <p>Lawyer: lawyer.shah@example.com / Aagam%1234</p>
            </div>
          </>
        ) : (
          <>
            <div className="mb-6 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <ShieldCheck size={26} />
              </div>
              <h1 className="text-2xl font-bold text-slate-900">Two-Factor Authentication</h1>
              <p className="text-sm text-slate-500">Enter the 6-digit code from your authenticator app</p>
              <p className="mt-1 text-xs text-slate-400">{mfaStep.user?.email || ''}</p>
            </div>
            <form onSubmit={onSubmitMfa} className="space-y-4">
              <div>
                <label className="label" htmlFor="mfa-code">Authentication code</label>
                <input
                  id="mfa-code"
                  className="input text-center text-2xl tracking-[0.5em]"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="••••••"
                  autoFocus
                  required
                />
              </div>
              <button type="submit" className="btn-primary w-full" disabled={loading || code.length !== 6}>
                {loading ? 'Verifying…' : 'Verify & Sign in'}
              </button>
              <button type="button" className="btn-secondary w-full" onClick={() => { setMfaStep(null); setCode(''); }}>
                <ArrowLeft size={15} /> Back
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
