import { api } from './auth';

const API_URL = 'http://localhost:8000';

export const getNotes = async () => {
  const response = await api.get('/api/notes');
  return response.data;
};

export const getNote = async (id) => {
  const response = await api.get(`/api/notes/${id}`);
  return response.data;
};

export const createNote = async (noteData) => {
  const response = await api.post('/api/notes', noteData);
  return response.data;
};

export const updateNote = async (id, noteData) => {
  const response = await api.put(`/api/notes/${id}`, noteData);
  return response.data;
};

export const deleteNote = async (id) => {
  const response = await api.delete(`/api/notes/${id}`);
  return response.data;
};

export const fetchPublicNotes = async () => {
  const response = await api.get('/api/notes/public');
  return response.data;
};