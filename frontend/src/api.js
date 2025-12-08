import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
});

// Add a request interceptor to include the token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const getRepos = () => api.get('/repos');
export const getRepoDocs = (repoId) => api.get('/docs', { params: { repo_id: repoId, limit: 10000 } });
export const getDocDetail = (slug) => api.get(`/docs/${slug}`);
export const getMembers = () => api.get('/members');
export const getMemberDocs = (userId) => api.get('/docs', { params: { user_id: userId, limit: 100 } });

// Social Features
export const followMember = (memberId) => api.post(`/members/${memberId}/follow`);
export const unfollowMember = (memberId) => api.post(`/members/${memberId}/unfollow`);

// Feed Features
export const getFeed = (filter = 'all') => api.get('/feed', { params: { filter } });
export const checkFeedStatus = () => api.get('/feed/status');
export const markFeedRead = () => api.post('/feed/read');

// Dashboard Features
export const getDashboardOverview = () => api.get('/dashboard/overview');
export const getDashboardTrends = (days = 30) => api.get('/dashboard/trends', { params: { days } });
export const getDashboardRankings = () => api.get('/dashboard/rankings');

// AI Features
export const searchDocs = (query) => api.post('/search', { query });
export const askAI = (query) => api.post('/chat/rag', { query });
export const explainDoc = (text) => api.post('/ai/explain', { text });

export default api;
