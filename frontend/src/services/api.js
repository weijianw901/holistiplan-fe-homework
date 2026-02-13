import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true // Important for session-based auth
});

// Request interceptor to handle authentication
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    const normalizedError = {
      status: error.response?.status,
      message:
        error.response?.data?.error ||
        error.message ||
        'Unexpected error occurred'
    }

    return Promise.reject(normalizedError)
  }
);

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (userData) => api.post('/auth/register', userData),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me'),
  updateProfile: (profileData) => api.put('/auth/profile', profileData)
};

// Users API
export const usersAPI = {
  getUsers: () => api.get('/users'),
  getUser: (id) => api.get(`/users/${id}`),
  createUser: (userData) => api.post('/users', userData),
  updateUser: (id, userData) => api.put(`/users/${id}`, userData),
  deleteUser: (id) => api.delete(`/users/${id}`)
};

// Servers API
export const serversAPI = {
  getServers: (params) => api.get('/servers', { params }),
  getServer: (id) => api.get(`/servers/${id}`),
  createServer: (serverData) => api.post('/servers', serverData),
  updateServer: (id, serverData) => api.put(`/servers/${id}`, serverData),
  deleteServer: (id) => api.delete(`/servers/${id}`)
};

// Dashboard API
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats')
};

export default api;
