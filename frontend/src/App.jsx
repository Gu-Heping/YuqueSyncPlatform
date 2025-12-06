import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import RepoList from './pages/RepoList';
import RepoDetail from './pages/RepoDetail';
import Members from './pages/Members';
import ChatWidget from './components/ChatWidget';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="repos" element={<RepoList />} />
          <Route path="repos/:repoId" element={<RepoDetail />} />
          <Route path="repos/:repoId/docs/:docSlug" element={<RepoDetail />} />
          <Route path="members" element={<Members />} />
        </Route>
      </Routes>
      <ChatWidget />
    </Router>
  );
}

export default App;
