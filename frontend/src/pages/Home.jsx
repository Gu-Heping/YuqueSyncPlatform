import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Users } from 'lucide-react';

const Home = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
      <Link
        to="/repos"
        className="group block p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <div className="flex items-center mb-4">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-full group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
            <BookOpen className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
          <h5 className="ml-4 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">知识库列表</h5>
        </div>
        <p className="font-normal text-gray-700 dark:text-gray-300">
          浏览所有已同步的语雀知识库，查看文档详情和目录结构。
        </p>
      </Link>

      <Link
        to="/members"
        className="group block p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        <div className="flex items-center mb-4">
          <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-full group-hover:bg-green-200 dark:group-hover:bg-green-900/50 transition-colors">
            <Users className="w-8 h-8 text-green-600 dark:text-green-400" />
          </div>
          <h5 className="ml-4 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">团队成员</h5>
        </div>
        <p className="font-normal text-gray-700 dark:text-gray-300">
          查看团队成员列表，搜索成员并查看其贡献的文档。
        </p>
      </Link>
    </div>
  );
};

export default Home;
