'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { User, Lock, Save, ShieldCheck } from 'lucide-react';
import AppShell from '@/components/AppShell';
import { Card, SectionTitle, RoleBadge, Badge } from '@/components/ui';
import { authApi } from '@/lib/services';
import { useAuth } from '@/lib/auth';
import { getErrorMessage } from '@/lib/api';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const qc = useQueryClient();
  const { user, fetchProfile } = useAuth();

  const profileQ = useQuery({ queryKey: ['profile'], queryFn: () => authApi.profile().then((r) => r.data) });
  const mfaQ = useQuery({ queryKey: ['mfa'], queryFn: () => authApi.mfaStatus().then((r) => r.data) });
  const me = profileQ.data || user;

  const [profile, setProfile] = useState({
    username: me?.username || '',
    first_name: me?.first_name || '',
    last_name: me?.last_name || '',
    email: me?.email || '',
  });
  const [pw, setPw] = useState({ current_password: '', new_password: '', new_password_confirm: '' });

  const saveProfile = useMutation({
    mutationFn: (d: any) => authApi.updateProfile(d),
    onSuccess: async () => {
      toast.success('Profile updated');
      await fetchProfile();
      qc.invalidateQueries({ queryKey: ['profile'] });
    },
    onError: (e: any) => toast.error(getErrorMessage(e)),
  });

  const changePw = useMutation({
    mutationFn: (d: any) => authApi.changePassword(d),
    onSuccess: () => {
      toast.success('Password changed');
      setPw({ current_password: '', new_password: '', new_password_confirm: '' });
    },
    onError: (e: any) => toast.error(getErrorMessage(e)),
  });

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setProfile((f) => ({ ...f, [k]: e.target.value }));
  const setP = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setPw((f) => ({ ...f, [k]: e.target.value }));

  return (
    <AppShell>
      <SectionTitle title="Settings" subtitle="Manage your account details and password" />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><User size={16} /> Profile</h3>
          <div className="mb-3 flex items-center gap-2">
            <RoleBadge role={me?.role} />
            <span className="text-xs text-slate-400">{me?.professional_id || 'no professional ID'}</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><label className="label">Username</label><input className="input" value={profile.username} onChange={set('username')} /></div>
            <div><label className="label">Email</label><input className="input" type="email" value={profile.email} onChange={set('email')} /></div>
            <div><label className="label">First name</label><input className="input" value={profile.first_name} onChange={set('first_name')} /></div>
            <div><label className="label">Last name</label><input className="input" value={profile.last_name} onChange={set('last_name')} /></div>
          </div>
          <button className="btn-primary mt-4" disabled={saveProfile.isPending} onClick={() => saveProfile.mutate(profile)}>
            <Save size={15} /> {saveProfile.isPending ? 'Saving…' : 'Save Profile'}
          </button>
        </Card>

        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><ShieldCheck size={16} /> Two-Factor Authentication (MFA-ready)</h3>
          {mfaQ.isLoading ? <p className="text-sm text-slate-400">Checking…</p> : mfaQ.data && (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Badge tone={mfaQ.data.mfa_enabled ? 'green' : mfaQ.data.mfa_available ? 'amber' : 'slate'}>
                  {mfaQ.data.mfa_enabled ? 'Enabled' : mfaQ.data.mfa_available ? 'Available' : 'Not available'}
                </Badge>
                {mfaQ.data.provider && <span className="text-xs text-slate-400">Provider: {mfaQ.data.provider}</span>}
              </div>
              <p className="text-xs text-slate-400">{mfaQ.data.note}</p>
            </div>
          )}
        </Card>

        <Card>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><Lock size={16} /> Change Password</h3>
          <div className="space-y-3">
            <div><label className="label">Current password</label>
              <input className="input" type="password" value={pw.current_password} onChange={setP('current_password')} /></div>
            <div><label className="label">New password (min 8, uppercase+digit+special)</label>
              <input className="input" type="password" value={pw.new_password} onChange={setP('new_password')} /></div>
            <div><label className="label">Confirm new password</label>
              <input className="input" type="password" value={pw.new_password_confirm} onChange={setP('new_password_confirm')} /></div>
          </div>
          <button
            className="btn-primary mt-4"
            disabled={changePw.isPending || !pw.current_password || !pw.new_password || pw.new_password !== pw.new_password_confirm}
            onClick={() => changePw.mutate(pw)}
          >
            <Lock size={15} /> {changePw.isPending ? 'Changing…' : 'Change Password'}
          </button>
        </Card>
      </div>
    </AppShell>
  );
}
