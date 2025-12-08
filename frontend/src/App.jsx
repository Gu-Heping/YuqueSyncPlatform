import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import RepoList from './pages/RepoList';
import RepoDetail from './pages/RepoDetail';
import Members from './pages/Members';
import Dashboard from './pages/Dashboard';
import LoginPage from './pages/LoginPage';
import Profile from './pages/Profile';
import ChatWidget from './components/ChatWidget';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="repos" element={<RepoList />} />
            <Route path="repos/:repoId" element={<RepoDetail />} />
            <Route path="repos/:repoId/docs/:docSlug" element={<RepoDetail />} />
            <Route path="members" element={<Members />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="profile" element={<Profile />} />
          </Route>
        </Routes>
        <ChatWidget />
      </Router>
    </AuthProvider>
  );
}

export default App;
