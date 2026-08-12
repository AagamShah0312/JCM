'use client';

import { create } from 'zustand';
import type { Role, User } from '@/types';
import { authApi } from './services';
import { clearTokens, getAccessToken, getErrorMessage, setTokens } from './api';

interface AuthState {
  user: User | null;
  hydrated: boolean;
  login: (email: string, password: string) => Promise<
    | { success: true }
    | { success: false; error: string; mfaRequired?: false }
    | { success: false; mfaRequired: true; mfaToken?: string; mfaUser?: User; error?: string }
  >;
  loginMfa: (token: string, code: string) => Promise<{ success: boolean; error?: string }>;
  register: (payload: Record<string, unknown>) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export function homeForRole(role?: Role | string | null): string {
  switch (role) {
    case 'admin':
      return '/admin';
    case 'judge':
      return '/judge';
    case 'lawyer':
      return '/lawyer';
    case 'guest':
      return '/guest/search';
    default:
      return '/login';
  }
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  hydrated: false,

  hydrate: async () => {
    if (get().hydrated) return;
    const token = getAccessToken();
    if (!token) {
      set({ hydrated: true, user: null });
      return;
    }
    try {
      const { data } = await authApi.profile();
      set({ user: data, hydrated: true });
    } catch {
      clearTokens();
      set({ user: null, hydrated: true });
    }
  },

  fetchProfile: async () => {
    const { data } = await authApi.profile();
    set({ user: data });
  },

  login: async (email, password) => {
    try {
      const { data } = await authApi.login(email, password);
      if (data.mfa_required) {
        return { success: false, mfaRequired: true, mfaToken: data.mfa_token, mfaUser: data.user };
      }
      setTokens(data.access, data.refresh);
      set({ user: data.user });
      return { success: true };
    } catch (e) {
      return { success: false, error: getErrorMessage(e) };
    }
  },

  loginMfa: async (token, code) => {
    try {
      const { data } = await authApi.mfaChallenge(token, code);
      setTokens(data.access, data.refresh);
      set({ user: data.user });
      return { success: true };
    } catch (e) {
      return { success: false, error: getErrorMessage(e) };
    }
  },

  register: async (payload) => {
    try {
      await authApi.register(payload);
      return { success: true };
    } catch (e) {
      return { success: false, error: getErrorMessage(e) };
    }
  },

  logout: async () => {
    try {
      const { getRefreshToken } = await import('./api');
      await authApi.logout(getRefreshToken());
    } catch {
      /* ignore */
    }
    clearTokens();
    set({ user: null });
  },
}));

// Kick off hydration in the browser so returning users stay signed in.
if (typeof window !== 'undefined') {
  void useAuth.getState().hydrate();
}
