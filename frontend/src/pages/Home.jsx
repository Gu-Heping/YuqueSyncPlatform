import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Users, Activity, Bell } from 'lucide-react';
import { getFeed, checkFeedStatus, markFeedRead } from '../api';
import ActivityItem from '../components/ActivityItem';
import { useAuth } from '../context/AuthContext';

const Home = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [feed, setFeed] = useState([]);
  const [hasNewFeed, setHasNewFeed] = useState(false);
  const [feedFilter, setFeedFilter] = useState('all'); // all | following
  const [loading, setLoading] = useState(false);

  // Check for new feed status
  useEffect(() => {
    const checkStatus = async () => {
      if (!user) return;
      try {
        const res = await checkFeedStatus();
        setHasNewFeed(res.data.has_new);
      } catch (error) {
        console.error("Failed to check feed status", error);
      }
    };
    checkStatus();
    // Poll every minute
    const interval = setInterval(checkStatus, 60000);
    return () => clearInterval(interval);
  }, [user]);

  // Fetch feed when tab is active or filter changes
  useEffect(() => {
    if (activeTab === 'activity' && user) {
      const fetchFeed = async () => {
        setLoading(true);
        try {
          const res = await getFeed(feedFilter);
          setFeed(res.data);
          
          // Mark as read if we have new items
          if (hasNewFeed) {
            await markFeedRead();
            setHasNewFeed(false);
          }
        } catch (error) {
          console.error("Failed to fetch feed", error);
        } finally {
          setLoading(false);
        }
      };
      fetchFeed();
    }
  }, [activeTab, feedFilter, user]);

  // Helper to merge adjacent activities for same doc
  const processFeed = (feedList) => {
    if (!feedList || feedList.length === 0) return [];
    
    const result = [];
    let lastItem = null;
    
    for (const item of feedList) {
      // If same doc and same action type as previous (which is newer in time), skip this one
      // This effectively keeps the latest activity for a sequence of updates on the same doc
      if (lastItem && 
          lastItem.doc_uuid === item.doc_uuid && 
          lastItem.action_type === item.action_type) {
         continue;
      }
      result.push(item);
      lastItem = item;
    }
    return result;
  };

  return (
    <div className="mt-6">
      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-fit mb-6">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
            activeTab === 'overview'
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          概览
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`relative px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center ${
            activeTab === 'activity'
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          动态
          {hasNewFeed && (
            <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full"></span>
          )}
        </button>
      </div>

      {/* Content */}
      {activeTab === 'overview' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
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
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Feed Header & Filter */}
          <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <Activity className="w-5 h-5 mr-2 text-blue-500" />
              最新动态
            </h3>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setFeedFilter('all')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  feedFilter === 'all'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'
                }`}
              >
                全部
              </button>
              <button
                onClick={() => setFeedFilter('following')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  feedFilter === 'following'
                    ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'
                }`}
              >
                关注
              </button>
            </div>
          </div>

          {/* Feed List */}
          <div className="min-h-[300px]">
            {loading ? (
              <div className="flex justify-center items-center h-40 text-gray-500">
                加载中...
              </div>
            ) : feed.length > 0 ? (
              <div>
                {processFeed(feed).map((item) => (
                  <ActivityItem key={item._id} activity={item} />
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <Bell className="w-12 h-12 mb-2 opacity-20" />
                <p>暂无动态</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
