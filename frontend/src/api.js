import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
});

export const getRepos = () => api.get('/repos');
export const getRepoDocs = (repoId) => api.get('/docs', { params: { repo_id: repoId, limit: 10000 } });
export const getDocDetail = (slug) => api.get(`/docs/${slug}`);
export const getMembers = () => api.get('/members');
export const getMemberDocs = (userId) => api.get('/docs', { params: { user_id: userId, limit: 100 } });

// AI Features
export const searchDocs = (query) => api.post('/search', { query });
export const askAI = (query) => api.post('/chat/rag', { query });
export const explainDoc = (text) => api.post('/ai/explain', { text });

export default api;
