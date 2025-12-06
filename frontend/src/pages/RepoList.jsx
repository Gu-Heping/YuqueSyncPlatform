import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getRepos } from '../api';
import { Book } from 'lucide-react';

const RepoList = () => {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const response = await getRepos();
        setRepos(response.data);
      } catch (error) {
        console.error('Failed to fetch repos:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchRepos();
  }, []);

  if (loading) return <div className="text-center py-10">加载中...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-gray-900">知识库列表</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {repos.map((repo) => (
          <Link
            key={repo.yuque_id}
            to={`/repos/${repo.yuque_id}`}
            className="block p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-xl font-semibold text-gray-900 truncate" title={repo.name}>
                {repo.name}
              </h2>
              <Book className="w-5 h-5 text-gray-400" />
            </div>
            <p className="text-gray-600 text-sm mb-4 line-clamp-2 h-10">
              {repo.description || '暂无简介'}
            </p>
            <div className="flex items-center text-sm text-gray-500">
              <span className="bg-gray-100 px-2 py-1 rounded">
                {repo.items_count} 篇文档
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default RepoList;
