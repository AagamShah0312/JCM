import React, { useState } from 'react';
import { authAPI } from '../services/api';
import { useAuthStore } from '../context/authStore';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const { user, getProfile } = useAuthStore();
  const [profileForm, setProfileForm] = useState({
    username: user?.username || '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    email: user?.email || '',
  });
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    new_password_confirm: '',
  });
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const onProfileChange = (e) => {
    setProfileForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const onPasswordChange = (e) => {
    setPasswordForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const saveProfile = async (e) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await authAPI.updateProfile(profileForm);
      await getProfile();
      toast.success('Profile updated');
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (e) => {
    e.preventDefault();
    setSavingPassword(true);
    try {
      await authAPI.changePassword(passwordForm);
      setPasswordForm({ current_password: '', new_password: '', new_password_confirm: '' });
      toast.success('Password changed successfully');
    } catch (error) {
      const data = error?.response?.data;
      if (data && typeof data === 'object') {
        const key = Object.keys(data)[0];
        const value = data[key];
        toast.error(Array.isArray(value) ? value[0] : String(value));
      } else {
        toast.error('Failed to change password');
      }
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">Manage account details and password</p>
      </div>

      <form onSubmit={saveProfile} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Profile</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <input name="username" value={profileForm.username} onChange={onProfileChange} placeholder="Username" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" />
          <input name="email" type="email" value={profileForm.email} onChange={onProfileChange} placeholder="Email" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" required />
          <input name="first_name" value={profileForm.first_name} onChange={onProfileChange} placeholder="First Name" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" required />
          <input name="last_name" value={profileForm.last_name} onChange={onProfileChange} placeholder="Last Name" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" />
        </div>
        <button disabled={savingProfile} className="bg-blue-600 text-white px-4 py-2 rounded-lg">{savingProfile ? 'Saving...' : 'Save Profile'}</button>
      </form>

      <form onSubmit={savePassword} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Change Password</h2>
        <div className="grid md:grid-cols-3 gap-4">
          <input type="password" name="current_password" value={passwordForm.current_password} onChange={onPasswordChange} placeholder="Current Password" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" required />
          <input type="password" name="new_password" value={passwordForm.new_password} onChange={onPasswordChange} placeholder="New Password" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" required />
          <input type="password" name="new_password_confirm" value={passwordForm.new_password_confirm} onChange={onPasswordChange} placeholder="Confirm New Password" className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100" required />
        </div>
        <button disabled={savingPassword} className="bg-blue-600 text-white px-4 py-2 rounded-lg">{savingPassword ? 'Updating...' : 'Update Password'}</button>
      </form>
    </div>
  );
}