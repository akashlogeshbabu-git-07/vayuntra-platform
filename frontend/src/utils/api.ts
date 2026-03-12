import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('vayuntra_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('vayuntra_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const fetchDashboardStats = (windowHours = 24) =>
  api.get(`/dashboard/stats?window_hours=${windowHours}`).then(r => r.data);

export const fetchThreats = (params?: any) =>
  api.get('/threats/', { params }).then(r => r.data);

export const fetchThreatStats = (windowHours = 24) =>
  api.get(`/threats/stats?window_hours=${windowHours}`).then(r => r.data);

export const fetchThreat = (id: string) =>
  api.get(`/threats/${id}`).then(r => r.data);

export const updateThreat = (id: string, data: any) =>
  api.patch(`/threats/${id}`, data).then(r => r.data);

export const isolateThreat = (id: string, data: any) =>
  api.post(`/threats/${id}/isolate`, data).then(r => r.data);

export const remediateThreat = (id: string) =>
  api.post(`/threats/${id}/remediate`, {}).then(r => r.data);

export const fetchAgents = (params?: any) =>
  api.get('/agents/', { params }).then(r => r.data);

export const fetchRecentThreats = (params?: any) =>
  api.get('/threats/', { params: { page_size: 10, ...params } }).then(r => r.data);

export const login = (email: string, password: string) => {
  const form = new URLSearchParams();
  form.append('username', email);
  form.append('password', password);
  return axios.post(`${API_BASE}/api/v1/auth/login`, form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  }).then(r => r.data);
};
