import axios from 'axios';
import { toast } from 'react-hot-toast';

// Configure your API base URL here
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    if (!error.response) {
      console.error('Network Error Details:', error);
      toast.error('Cannot connect to the server. Please ensure the backend is running.');
      return Promise.reject(error);
    }

    // Handle authentication errors
    if (error.response.status === 401 || error.response.status === 403) {
      localStorage.removeItem('authToken');
      localStorage.removeItem('userRole');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    if (error.response.status === 422) {
      const validationErrors = error.response.data.detail;
      if (Array.isArray(validationErrors)) {
        validationErrors.forEach((err: any) => {
          toast.error(`Validation error: ${err.msg}`);
        });
      } else {
        toast.error('Invalid data provided. Please check your input.');
      }
      return Promise.reject(error);
    }

    switch (error.response.status) {
      case 404:
        toast.error('Resource not found');
        break;
      case 500:
        toast.error('Server error. Please try again later.');
        break;
      default:
        const message = error.response?.data?.detail || 'An error occurred';
        toast.error(message);
    }

    return Promise.reject(error);
  }
);

// Login function
export const login = async (username: string, password: string) => {
  const response = await api.post('/auth/login', { username, password });
  const { token, role } = response.data;
  localStorage.setItem('authToken', token);
  localStorage.setItem('userRole', role);
  return { token, role };
};

// Helper functions for role checking
export const isAdmin = () => {
  return localStorage.getItem('userRole') === 'admin';
};

export const hasManageAccess = () => {
  const role = localStorage.getItem('userRole');
  return role === 'admin' || role === 'manager';
};

export const getCurrentUser = () => {
  const token = localStorage.getItem('authToken');
  const role = localStorage.getItem('userRole');
  return token ? { token, role } : null;
};

export const logout = () => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('userRole');
  window.location.href = '/login';
};

// Export the api instance for custom requests
export default api;

