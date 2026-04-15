import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

export const login = () => {
  window.location.href = `${API_URL}/auth/login`;
};

export const logout = async () => {
  try {
    await axios.post(`${API_URL}/auth/logout`, {}, { withCredentials: true });
  } finally {
    window.location.href = '/login';
  }
};

export const refreshSession = async () => {
  const response = await api.post('/auth/refresh');
  return response.data;
};

export const checkAuth = async () => {
  try {
    const { data } = await api.get('/api/me');
    return data;
  } catch {
    return null;
  }
};