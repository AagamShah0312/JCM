import axios, { AxiosError, type AxiosInstance } from 'axios';

const TOKEN_KEY = 'jcm_access';
const REFRESH_KEY = 'jcm_refresh';

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access?: string | null, refresh?: string | null) {
  if (typeof window === 'undefined') return;
  if (access) localStorage.setItem(TOKEN_KEY, access);
  else localStorage.removeItem(TOKEN_KEY);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  else if (refresh === null) localStorage.removeItem(REFRESH_KEY);
}

export function clearTokens() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/**
 * Browser calls go through the Next.js rewrite (`/api/*` → Django).
 * This keeps cookies/CORS simple and works in Docker/preview hosts.
 */
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Let the browser set multipart boundaries.
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    if (config.headers) {
      delete (config.headers as Record<string, unknown>)['Content-Type'];
    }
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const { data } = await axios.post('/api/auth/token/refresh/', { refresh });
    const access = data.access as string;
    setTokens(access, data.refresh || refresh);
    return access;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      if (!refreshing) refreshing = refreshAccessToken().finally(() => { refreshing = null; });
      const access = await refreshing;
      if (access && original.headers) {
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

export function getErrorMessage(error: unknown): string {
  const err = error as AxiosError<any>;
  const data = err?.response?.data;
  if (!data) return err?.message || 'Request failed';
  if (typeof data === 'string') return data;
  if (data.error?.message) return data.error.message;
  if (data.error && typeof data.error === 'string') return data.error;
  if (data.detail) return Array.isArray(data.detail) ? data.detail[0] : data.detail;
  if (data.message) return data.message;
  if (typeof data.non_field_errors?.[0] === 'string') return data.non_field_errors[0];
  const firstKey = Object.keys(data)[0];
  if (firstKey) {
    const val = data[firstKey];
    if (Array.isArray(val)) return `${firstKey}: ${val[0]}`;
    if (typeof val === 'string') return val;
  }
  return 'Request failed';
}

export default api;
