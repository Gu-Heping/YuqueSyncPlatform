import React, { useState, useEffect } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { Book, Users, Home, Search } from 'lucide-react';
import SearchModal from './SearchModal';

const Layout = () => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex-shrink-0 flex items-center text-blue-600 font-bold text-xl">
                <Book className="w-6 h-6 mr-2" />
                YuqueSync
              </Link>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/repos"
                  className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  知识库
                </Link>
                <Link
                  to="/members"
                  className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  团队成员
                </Link>
              </div>
            </div>
            
            {/* Search Trigger */}
            <div className="flex items-center">
              <button
                onClick={() => setIsSearchOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-500 rounded-lg text-sm transition-colors"
              >
                <Search className="w-4 h-4" />
                <span className="hidden sm:inline">搜索文档...</span>
                <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-xs font-semibold text-gray-500 bg-white border border-gray-200 rounded-md shadow-sm">
                  ⌘K
                </kbd>
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      
      <SearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  );
};

export default Layout;
