'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { User, Lock, Save, ShieldCheck, QrCode, Trash2, KeyRound, RefreshCw, Fingerprint } from 'lucide-react';
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

        <MfaCard />

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

/* ------------------------------------------------------------------ */
/* Two-Factor Authentication card (spec §46): status, enroll (QR),
   verify, disable. Full TOTP flow supported by the backend.            */
/* ------------------------------------------------------------------ */
function MfaCard() {
  const qc = useQueryClient();
  const mfaQ = useQuery({ queryKey: ['mfa'], queryFn: () => authApi.mfaStatus().then((r) => r.data) });
  const recoveryQ = useQuery({ queryKey: ['mfa-recovery'], queryFn: () => authApi.mfaRecoveryCodes().then((r) => r.data), enabled: false });
  const webauthnQ = useQuery({ queryKey: ['mfa-webauthn'], queryFn: () => authApi.mfaWebAuthn().then((r) => r.data), enabled: false });
  const [enrollData, setEnrollData] = useState<any>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = () => { qc.invalidateQueries({ queryKey: ['mfa'] }); setRecoveryCodes(null); };

  const enroll = async () => {
    setBusy(true);
    try {
      const r = await authApi.mfaEnroll();
      setEnrollData(r.data);
      toast.success('Scan the QR code with your authenticator app');
    } catch (e: any) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    setBusy(true);
    try {
      const r = await authApi.mfaVerify(code);
      toast.success('Two-factor authentication enabled');
      if (r.data?.recovery_codes?.length) {
        setRecoveryCodes(r.data.recovery_codes);
      }
      setEnrollData(null);
      setCode('');
      refresh();
    } catch (e: any) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const showRecovery = async () => {
    try {
      const r = await authApi.mfaRecoveryCodes();
      const used = (r.data?.recovery_codes || []).filter((c: any) => c.used).length;
      toast(`${used} of ${(r.data?.recovery_codes || []).length} recovery code(s) used`, { icon: '🔑' });
      recoveryQ.refetch();
    } catch (e: any) {
      toast.error(getErrorMessage(e));
    }
  };

  const regenerateRecovery = async () => {
    if (!window.confirm('Regenerate recovery codes? Previous unused codes will stop working.')) return;
    setBusy(true);
    try {
      const r = await authApi.mfaRegenerateRecovery();
      setRecoveryCodes(r.data?.recovery_codes || []);
      toast.success('New recovery codes generated — save them');
    } catch (e: any) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    const c = window.prompt('Enter your current 6-digit code to disable 2FA:');
    if (!c) return;
    setBusy(true);
    try {
      await authApi.mfaDisable(c);
      toast.success('Two-factor authentication disabled');
      setCode('');
      refresh();
    } catch (e: any) {
      toast.error(getErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  if (mfaQ.isLoading) return <Card><p className="text-sm text-slate-400">Checking…</p></Card>;

  const enabled = mfaQ.data?.mfa_enabled;
  const available = mfaQ.data?.mfa_available;

  return (
    <Card>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"><ShieldCheck size={16} /> Two-Factor Authentication</h3>

      <div className="mb-3 flex items-center gap-2 text-sm">
        <Badge tone={enabled ? 'green' : available ? 'amber' : 'slate'}>
          {enabled ? 'Enabled' : available ? 'Available' : 'Not available'}
        </Badge>
        {mfaQ.data?.provider && <span className="text-xs text-slate-400">Provider: {mfaQ.data.provider}</span>}
      </div>

      {!available && (
        <p className="text-xs text-slate-400">
          {mfaQ.data?.note || 'MFA is disabled on this instance. Set MFA_ENABLED=True in the backend .env to activate.'}
        </p>
      )}

      {available && !enabled && !enrollData && (
        <button className="btn-secondary" disabled={busy} onClick={enroll}>
          <QrCode size={15} /> {busy ? 'Generating…' : 'Set up authenticator app'}
        </button>
      )}

      {enrollData && (
        <div className="mt-2 space-y-3">
          <div className="flex items-start gap-3 rounded-md bg-slate-50 p-3">
            {enrollData.qr_png && <img src={enrollData.qr_png} alt="QR" className="h-36 w-36 rounded border border-slate-200 bg-white" />}
            <div className="text-xs text-slate-500">
              <p className="font-semibold text-slate-700">Scan with Google Authenticator / Authy</p>
              <p className="mt-1">Account: <b>{enrollData.account}</b></p>
              <p>Issuer: <b>{enrollData.issuer}</b></p>
              <p className="mt-1">Or enter the secret manually:</p>
              <code className="block break-all rounded bg-white px-2 py-1 font-mono text-[11px] text-slate-700">{enrollData.secret}</code>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              className="input w-40 text-center text-lg tracking-widest"
              inputMode="numeric" maxLength={6} value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="••••••"
            />
            <button className="btn-primary" disabled={busy || code.length !== 6} onClick={verify}>
              {busy ? 'Verifying…' : 'Verify & Enable'}
            </button>
            <button className="btn-secondary" disabled={busy} onClick={() => setEnrollData(null)}>Cancel</button>
          </div>
        </div>
      )}

      {enabled && (
        <div className="space-y-3">
          {recoveryCodes && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
              <p className="mb-2 text-xs font-semibold uppercase text-amber-700">Recovery codes — save these somewhere safe (shown once)</p>
              <div className="grid grid-cols-2 gap-1 font-mono text-sm text-slate-800">
                {recoveryCodes.map((c, i) => <code key={i}>{c}</code>)}
              </div>
              <button className="btn-secondary mt-2 text-xs" onClick={() => setRecoveryCodes(null)}>Hide</button>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" disabled={busy} onClick={showRecovery}>
              <KeyRound size={14} /> Recovery codes
            </button>
            <button className="btn-secondary" disabled={busy} onClick={regenerateRecovery}>
              <RefreshCw size={14} /> Regenerate
            </button>
            <button className="btn-danger" disabled={busy} onClick={disable}>
              <Trash2 size={15} /> Disable
            </button>
          </div>
          <button className="btn-secondary text-xs" onClick={() => webauthnQ.refetch()}>
            <Fingerprint size={14} /> WebAuthn / Passkeys
          </button>
          {webauthnQ.data && (
            <p className="text-xs text-slate-400">{webauthnQ.data.note} ({webauthnQ.data.registered_credentials?.length || 0} credential(s))</p>
          )}
        </div>
      )}
    </Card>
  );
}
