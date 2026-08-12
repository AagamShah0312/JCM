/**
 * API Service - Handles all communication with backend
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle responses
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        });

        localStorage.setItem('access_token', response.data.access);
        apiClient.defaults.headers.Authorization = `Bearer ${response.data.access}`;
        return apiClient(originalRequest);
      } catch (err) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(err);
      }
    }

    return Promise.reject(error);
  }
);

// Authentication APIs
export const authAPI = {
  register: (data) => apiClient.post('/auth/register/', data),
  login: (data) => apiClient.post('/auth/login/', data),
  logout: () => apiClient.post('/auth/logout/', {}),
  getProfile: () => apiClient.get('/auth/profile/'),
  updateProfile: (data) => apiClient.put('/auth/profile/', data),
  changePassword: (data) => apiClient.post('/auth/change-password/', data),
  listUsers: (params) => apiClient.get('/auth/users/', { params }),
  importStaffCSV: (role, file) => {
    const formData = new FormData();
    formData.append('role', role);
    formData.append('file', file);
    return apiClient.post('/auth/users/import_staff_csv/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  promoteDemote: (id, data) => apiClient.post(`/auth/users/${id}/promote_demote/`, data),
  userAnalytics: (id) => apiClient.get(`/auth/users/${id}/analytics/`),
};

// Cases APIs
export const casesAPI = {
  list: (params) => apiClient.get('/cases/', { params }),
  create: (data) => apiClient.post('/cases/', data),
  retrieve: (id) => apiClient.get(`/cases/${id}/`),
  update: (id, data) => apiClient.put(`/cases/${id}/`, data),
  partialUpdate: (id, data) => apiClient.patch(`/cases/${id}/`, data),
  delete: (id) => apiClient.delete(`/cases/${id}/`),
  getTimeline: (id) => apiClient.get(`/cases/${id}/timeline/`),
  addTimelineEvent: (id, data) => apiClient.post(`/cases/${id}/add_timeline_event/`, data),
  getNotes: (id) => apiClient.get(`/cases/${id}/notes/`),
  addNote: (id, data) => apiClient.post(`/cases/${id}/notes/`, data),
  assignLawyer: (id, data) => apiClient.post(`/cases/${id}/assign_lawyer/`, data),
  getUpcomingHearings: () => apiClient.get('/cases/upcoming_hearings/'),
  getStatistics: () => apiClient.get('/cases/statistics/'),
  bookmark: (id) => apiClient.post(`/cases/${id}/bookmark/`),
  unbookmark: (id) => apiClient.post(`/cases/${id}/unbookmark/`),
  bookmarked: () => apiClient.get('/cases/bookmarked/'),
  finish: (id) => apiClient.post(`/cases/${id}/finish/`),
  updateHearing: (id, data) => {
    if (typeof data === 'string') {
      return apiClient.post(`/cases/${id}/update_hearing/`, { next_hearing_date: data });
    }
    const formData = new FormData();
    formData.append('next_hearing_date', data.next_hearing_date);
    (data.files || []).forEach((item) => {
      if (item.file) {
        formData.append('files', item.file);
        formData.append('document_types', item.document_type || 'other');
        formData.append('descriptions', item.description || '');
      }
    });
    return apiClient.post(`/cases/${id}/update_hearing/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Documents APIs
export const documentsAPI = {
  list: (params) => apiClient.get('/documents/', { params }),
  upload: (caseId, data) => {
    const formData = new FormData();
    formData.append('case', caseId);
    if (data.files?.length) {
      data.files.forEach((item) => {
        if (item.file) {
          formData.append('files', item.file);
          formData.append('document_types', item.document_type || 'other');
          formData.append('descriptions', item.description || '');
        }
      });
    } else {
      formData.append('document_type', data.document_type);
      formData.append('file', data.file);
      if (data.description) formData.append('description', data.description);
    }

    return apiClient.post('/documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  retrieve: (id) => apiClient.get(`/documents/${id}/`),
  download: (id) => apiClient.get(`/documents/${id}/download/`),
  delete: (id) => apiClient.delete(`/documents/${id}/`),
  getExtraction: (id) => apiClient.get(`/documents/${id}/extraction/`),
};

// Notifications APIs
export const notificationsAPI = {
  list: (params) => apiClient.get('/notifications/', { params }),
  unread: () => apiClient.get('/notifications/unread/'),
  markAsRead: (id) => apiClient.post(`/notifications/${id}/mark_as_read/`),
  markAllAsRead: () => apiClient.post('/notifications/mark_all_as_read/'),
  clearOld: () => apiClient.delete('/notifications/clear_old/'),
};

// AI Assistant APIs
export const aiAPI = {
  createConversation: (caseId) => apiClient.post('/ai/conversations/', { case: caseId }),
  listConversations: (params) => apiClient.get('/ai/conversations/', { params }),
  getConversation: (id) => apiClient.get(`/ai/conversations/${id}/`),
  sendMessage: (id, content) => apiClient.post(`/ai/conversations/${id}/send_message/`, { content }),
  summarize: (id) => apiClient.post(`/ai/conversations/${id}/summarize/`),
  generateTimeline: (id) => apiClient.post(`/ai/conversations/${id}/generate_timeline/`),
  getQueryHistory: (params) => apiClient.get('/ai/queries/', { params }),
  getCaseChat: (caseId) => apiClient.get(`/ai/cases/${caseId}/chat/`),
  sendCaseMessage: (caseId, content) => apiClient.post(`/ai/cases/${caseId}/chat/`, { content }),
  explainCase: (caseId) => apiClient.get(`/ai/cases/${caseId}/explain/`),
};

// Audit APIs
export const auditAPI = {
  list: (params) => apiClient.get('/audit/logs/', { params }),
};

export default apiClient;
