/**
 * Authentication Store - Global state management with Zustand
 */
import { create } from 'zustand';
import { authAPI } from '../services/api';

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,

  // Initialize auth state from localStorage
  initializeAuth: () => {
    const token = localStorage.getItem('access_token');
    const user = localStorage.getItem('user');
    if (token && user) {
      set({
        isAuthenticated: true,
        user: JSON.parse(user),
      });
    }
  },

  // Register
  register: async (data) => {
    set({ isLoading: true });
    try {
      await authAPI.register(data);
      set({ isLoading: false });
      return { success: true };
    } catch (error) {
      set({ isLoading: false });
      const responseData = error.response?.data;
      if (typeof responseData === 'string') {
        return { success: false, error: responseData };
      }
      if (responseData?.detail) {
        return { success: false, error: responseData.detail };
      }
      if (responseData?.non_field_errors?.length) {
        return { success: false, error: responseData.non_field_errors[0] };
      }
      if (responseData && typeof responseData === 'object') {
        const firstField = Object.keys(responseData)[0];
        const value = responseData[firstField];
        const message = Array.isArray(value) ? value[0] : value;
        return { success: false, error: `${firstField}: ${message}` };
      }
      return { success: false, error: 'Registration failed' };
    }
  },

  // Login
  login: async (credentials) => {
    set({ isLoading: true });
    try {
      const response = await authAPI.login(credentials);
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      set({
        isAuthenticated: true,
        user: response.data.user,
        isLoading: false,
      });
      return { success: true };
    } catch (error) {
      set({ isLoading: false });
      const responseData = error.response?.data;
      if (responseData?.detail) {
        return { success: false, error: responseData.detail };
      }
      if (responseData?.non_field_errors?.length) {
        return { success: false, error: responseData.non_field_errors[0] };
      }
      if (typeof responseData === 'string') {
        return { success: false, error: responseData };
      }
      return { success: false, error: 'Login failed' };
    }
  },

  // Logout
  logout: async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    set({
      isAuthenticated: false,
      user: null,
    });
  },

  // Get profile
  getProfile: async () => {
    try {
      const response = await authAPI.getProfile();
      set({ user: response.data });
      localStorage.setItem('user', JSON.stringify(response.data));
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  },
}));
