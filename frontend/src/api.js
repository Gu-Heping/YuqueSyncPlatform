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

// Add a response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const getRepos = () => api.get('/repos');
export const getRepoDocs = (repoId) => api.get('/docs', { params: { repo_id: repoId, limit: 10000 } });
export const getDocDetail = (slug) => api.get(`/docs/${slug}`);
export const getMembers = (params) => api.get('/members', { params });
export const getMemberDocs = (userId) => api.get('/docs', { params: { user_id: userId, limit: 100 } });

// Social Features
export const followMember = (memberId) => api.post(`/members/${memberId}/follow`);
export const unfollowMember = (memberId) => api.post(`/members/${memberId}/unfollow`);
export const followAllMembers = (repoId) => api.post('/members/follow/all', null, { params: repoId ? { repo_id: repoId } : {} });
export const unfollowAllMembers = (repoId) => api.post('/members/unfollow/all', null, { params: repoId ? { repo_id: repoId } : {} });

// Feed Features
export const getFeed = (filter = 'all', repoId = null) => api.get('/feed/', { params: { filter, repo_id: repoId } });
export const checkFeedStatus = () => api.get('/feed/status');
export const markFeedRead = () => api.post('/feed/read');

// Dashboard Features
export const getDashboardOverview = (repoId = null) => api.get('/dashboard/overview', { params: { repo_id: repoId } });
export const getDashboardTrends = (days = 30, repoId = null) => api.get('/dashboard/trends', { params: { days, repo_id: repoId } });
export const getDashboardRankings = (repoId = null) => api.get('/dashboard/rankings', { params: { repo_id: repoId } });

// AI Features
export const searchDocs = (query) => api.post('/search', { query });
export const askAI = (query) => api.post('/chat/rag', { query });
export const explainDoc = (text) => api.post('/ai/explain', { text });

// Comment Features
export const getComments = (params) => api.get('/comments', { params });
export const checkCommentStatus = () => api.get('/comments/status');
export const markCommentsRead = () => api.post('/comments/read');
export const fetchDocComments = (docYuqueId) => api.get(`/comments/doc/${docYuqueId}`);

export default api;
