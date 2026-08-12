import api from './api';
import type { Case, Hearing, CaseDocument, Order, Task, NotificationItem, User } from '@/types';

/** Normalize DRF list responses (paginated or raw array). */
export function unwrapList<T = any>(data: any): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.hearings)) return data.hearings;
  return [];
}

export const authApi = {
  login: (email: string, password: string) => api.post('/auth/login/', { email, password }),
  register: (payload: Record<string, unknown>) => api.post('/auth/register/', payload),
  logout: (refresh?: string | null) => api.post('/auth/logout/', { refresh }),
  profile: () => api.get<User>('/auth/profile/'),
  updateProfile: (data: Partial<User>) => api.put('/auth/profile/', data),
  changePassword: (data: { current_password: string; new_password: string; new_password_confirm: string }) =>
    api.post('/auth/change-password/', data),
  mfaStatus: () => api.get('/auth/mfa/status/'),
  mfaEnroll: () => api.post('/auth/mfa/enroll/', {}),
  mfaVerify: (code: string) => api.post('/auth/mfa/verify/', { code }),
  mfaDisable: (code: string) => api.post('/auth/mfa/disable/', { code }),
  mfaChallenge: (mfa_token: string, code: string) => api.post('/auth/mfa/challenge/', { mfa_token, code }),
  mfaRecoveryCodes: () => api.get('/auth/mfa/recovery-codes/'),
  mfaRegenerateRecovery: () => api.post('/auth/mfa/recovery-codes/regenerate/', {}),
  mfaWebAuthn: () => api.get('/auth/mfa/webauthn/'),
};

export const casesApi = {
  list: (params?: Record<string, unknown>) => api.get<Case[] | { results: Case[]; count: number }>('/cases/', { params }),
  retrieve: (id: string) => api.get<Case>(`/cases/${id}/`),
  create: (data: Record<string, unknown>) => api.post<Case>('/cases/', data),
  update: (id: string, data: Record<string, unknown>) => api.patch<Case>(`/cases/${id}/`, data),
  timeline: (id: string) => api.get(`/cases/${id}/timeline/`),
  parties: (id: string) => api.get(`/cases/${id}/parties/`),
  addParty: (id: string, data: Record<string, unknown>) => api.post(`/cases/${id}/parties/`, data),
  changeStatus: (id: string, status: string) => api.post(`/cases/${id}/change_status/`, { status }),
};

export const hearingsApi = {
  list: (params?: Record<string, unknown>) => api.get<Hearing[] | { results: Hearing[] }>('/hearings/', { params }),
  retrieve: (id: string) => api.get<Hearing>(`/hearings/${id}/`),
  create: (data: Record<string, unknown>) => api.post<Hearing>('/hearings/', data),
  reschedule: (id: string, data: Record<string, unknown>) => api.post(`/hearings/${id}/reschedule/`, data),
  complete: (id: string, data: Record<string, unknown>) => api.post(`/hearings/${id}/complete/`, data),
  cancel: (id: string, data?: Record<string, unknown>) => api.post(`/hearings/${id}/cancel/`, data || {}),
  createParticipant: (id: string, data: Record<string, unknown>) => api.post(`/hearings/${id}/participants/`, data),
  participants: (id: string) => api.get(`/hearings/${id}/participants/`),
  proceedings: (id: string) => api.get(`/hearings/${id}/proceedings/`),
};

export const documentsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<CaseDocument[] | { results: CaseDocument[] }>('/documents/', { params }),
  retrieve: (id: string) => api.get<CaseDocument>(`/documents/${id}/`),
  upload: (caseId: string, files: File[], extra?: Record<string, string>) => {
    const fd = new FormData();
    fd.append('case', caseId);
    files.forEach((f) => fd.append('files', f));
    if (extra) Object.entries(extra).forEach(([k, v]) => { if (v) fd.append(k, v); });
    return api.post('/documents/', fd);
  },
  download: (id: string) => api.get<{ download_url: string }>(`/documents/${id}/download/`),
  compare: (id: string, versionA: number, versionB: number) =>
    api.post(`/documents/${id}/compare/`, { version_a: versionA, version_b: versionB }),
  setVisibility: (id: string, visibility: string) => api.post(`/documents/${id}/set_visibility/`, { visibility }),
};

export const ordersApi = {
  list: (params?: Record<string, unknown>) => api.get<Order[] | { results: Order[] }>('/orders/', { params }),
  retrieve: (id: string) => api.get<Order>(`/orders/${id}/`),
  create: (data: Record<string, unknown>) => api.post<Order>('/orders/', data),
  publish: (id: string) => api.post(`/orders/${id}/publish/`, {}),
  sign: (id: string) => api.post(`/orders/${id}/sign/`, {}),
};

export const tasksApi = {
  list: (params?: Record<string, unknown>) => api.get<Task[] | { results: Task[] }>('/tasks/', { params }),
  create: (data: Record<string, unknown>) => api.post<Task>('/tasks/', data),
  complete: (id: string) => api.post(`/tasks/${id}/complete/`, {}),
};

export const notificationsApi = {
  list: () => api.get<NotificationItem[] | { results: NotificationItem[] }>('/notifications/'),
  unread: () => api.get<{ count: number }>('/notifications/unread/'),
  markRead: (id: string) => api.post(`/notifications/${id}/mark_as_read/`, {}),
  markAll: () => api.post('/notifications/mark_all_as_read/', {}),
};

export const analyticsApi = {
  admin: () => api.get('/analytics/admin/'),
  causeList: (date: string, courtroom?: string) =>
    api.get('/analytics/cause-list/', { params: { date, courtroom } }),
  calendar: (start: string, end: string) =>
    api.get('/analytics/calendar/', { params: { start, end } }),
  caseHealth: (caseId: string) => api.get(`/analytics/cases/${caseId}/health/`),
  whatChanged: (caseId: string, since?: string) =>
    api.get(`/analytics/cases/${caseId}/what-changed/`, { params: since ? { since } : undefined }),
  scheduling: (caseId: string) => api.get(`/analytics/cases/${caseId}/scheduling-suggestions/`),
};

export const publicApi = {
  search: (params: Record<string, unknown>) => api.get('/public/cases/', { params }),
  detail: (id: string) => api.get(`/public/cases/${id}/`),
  hearings: (id: string) => api.get(`/public/cases/${id}/hearings/`),
  orders: (id: string) => api.get(`/public/cases/${id}/orders/`),
  documents: (id: string) => api.get(`/public/cases/${id}/documents/`),
};

export const searchApi = {
  global: (q: string) => api.get('/search/', { params: { q } }),
};

export const csvApi = {
  staffPreview: (role: string, file: File) => {
    const fd = new FormData();
    fd.append('role', role);
    fd.append('file', file);
    return api.post('/auth/csv/staff/preview/', fd);
  },
  staffImport: (role: string, rows: unknown[]) =>
    api.post('/auth/csv/staff/import/', { role, rows }),
  casesPreview: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/auth/csv/cases/preview/', fd);
  },
  casesImport: (rows: unknown[]) => api.post('/auth/csv/cases/import/', { rows }),
  errorReport: (type: string, role: string, file: File) => {
    const fd = new FormData();
    fd.append('type', type);
    fd.append('role', role);
    fd.append('file', file);
    return api.post('/auth/csv/error-report/', fd, { responseType: 'blob' });
  },
};

export const aiApi = {
  chat: async (caseId: string, content: string) => {
    const res = await api.post(`/ai/cases/${caseId}/chat/`, { content });
    const data = res.data || {};
    return {
      ...res,
      data: {
        ...data,
        answer: data.answer || data.assistant_message?.content || '',
        citations: data.citations || [],
        warnings: data.warnings || [],
        sources: data.sources || [],
      },
    };
  },
  explain: (caseId: string) => api.get(`/ai/cases/${caseId}/explain/`),
  documentsSummary: (caseId: string) => api.get(`/ai/cases/${caseId}/documents/summary/`),
  hearingSummary: (caseId: string, hearingId: string) =>
    api.get(`/ai/cases/${caseId}/hearing/${hearingId}/summary/`),
};

export const courtsApi = {
  list: () => api.get('/courts/'),
  courtrooms: () => api.get('/courts/courtrooms/'),
};
