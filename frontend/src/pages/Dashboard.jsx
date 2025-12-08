import React, { useState, useEffect } from 'react';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area 
} from 'recharts';
import { 
  FileText, Users, ThumbsUp, Eye, TrendingUp, Award, Calendar, Activity 
} from 'lucide-react';
import { getDashboardOverview, getDashboardTrends, getDashboardRankings } from '../api';
import { Link } from 'react-router-dom';

const StatCard = ({ title, value, icon: Icon, trend, color }) => (
  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
    <div className="flex items-center justify-between mb-4">
      <div className={`p-3 rounded-full ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      {trend && (
        <div className="flex items-center text-green-500 text-sm font-medium">
          <TrendingUp className="w-4 h-4 mr-1" />
          {trend}
        </div>
      )}
    </div>
    <h3 className="text-gray-500 dark:text-gray-400 text-sm font-medium">{title}</h3>
    <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
  </div>
);

const RankingList = ({ title, data, icon: Icon, valueLabel }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
    <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center">
      <Icon className="w-5 h-5 mr-2 text-blue-500" />
      <h3 className="font-semibold text-gray-900 dark:text-white">{title}</h3>
    </div>
    <div className="divide-y divide-gray-100 dark:divide-gray-700">
      {data.map((item, index) => (
        <div key={item.user_id} className="p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
          <div className="flex items-center">
            <div className={`
              w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mr-3
              ${index === 0 ? 'bg-yellow-100 text-yellow-600' : 
                index === 1 ? 'bg-gray-100 text-gray-600' : 
                index === 2 ? 'bg-orange-100 text-orange-600' : 'bg-blue-50 text-blue-500'}
            `}>
              {index + 1}
            </div>
            <Link to={`/members/${item.user_id}`} className="flex items-center group">
              <img 
                src={item.avatar_url || `https://ui-avatars.com/api/?name=${item.name}`} 
                alt={item.name}
                className="w-8 h-8 rounded-full mr-3 border border-gray-200 dark:border-gray-600"
              />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-200 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                {item.name}
              </span>
            </Link>
          </div>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {item.value.toLocaleString()} {valueLabel}
          </span>
        </div>
      ))}
      {data.length === 0 && (
        <div className="p-8 text-center text-gray-500 dark:text-gray-400 text-sm">
          暂无数据
        </div>
      )}
    </div>
  </div>
);

const Dashboard = () => {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [rankings, setRankings] = useState({ word_rankings: [], like_rankings: [], read_rankings: [] });
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30'); // days

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - parseInt(dateRange));

        const [overviewRes, trendsRes, rankingsRes] = await Promise.all([
          getDashboardOverview(),
          getDashboardTrends({ 
            start_date: startDate.toISOString(), 
            end_date: endDate.toISOString() 
          }),
          getDashboardRankings()
        ]);

        setOverview(overviewRes.data);
        setTrends(trendsRes.data);
        setRankings(rankingsRes.data);
      } catch (error) {
        console.error("Failed to fetch dashboard data", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dateRange]);

  if (loading && !overview) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">数据看板</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          实时监控团队知识库的活跃度与贡献情况
        </p>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard 
            title="总文档数" 
            value={overview.total_docs.toLocaleString()} 
            icon={FileText} 
            color="bg-blue-500"
            trend={`今日 +${overview.new_docs_today}`}
          />
          <StatCard 
            title="总字数" 
            value={(overview.total_words / 10000).toFixed(1) + '万'} 
            icon={Activity} 
            color="bg-green-500"
          />
          <StatCard 
            title="总阅读" 
            value={overview.total_reads.toLocaleString()} 
            icon={Eye} 
            color="bg-purple-500"
          />
          <StatCard 
            title="总点赞" 
            value={overview.total_likes.toLocaleString()} 
            icon={ThumbsUp} 
            color="bg-orange-500"
          />
        </div>
      )}

      {/* Trends Chart */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">活跃趋势</h3>
          <select 
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5"
          >
            <option value="7">最近 7 天</option>
            <option value="30">最近 30 天</option>
            <option value="90">最近 90 天</option>
          </select>
        </div>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trends} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorDocs" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="date" 
                stroke="#9CA3AF" 
                fontSize={12}
                tickFormatter={(str) => str.slice(5)} // Show MM-DD
              />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="new_docs" 
                name="新增文档" 
                stroke="#3B82F6" 
                fillOpacity={1} 
                fill="url(#colorDocs)" 
              />
              <Area 
                type="monotone" 
                dataKey="active_users" 
                name="活跃人数" 
                stroke="#10B981" 
                fillOpacity={1} 
                fill="url(#colorUsers)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Rankings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <RankingList 
          title="笔耕不辍榜" 
          data={rankings.word_rankings} 
          icon={FileText} 
          valueLabel="字"
        />
        <RankingList 
          title="人气之星榜" 
          data={rankings.like_rankings} 
          icon={ThumbsUp} 
          valueLabel="赞"
        />
        <RankingList 
          title="知识传播榜" 
          data={rankings.read_rankings} 
          icon={Eye} 
          valueLabel="阅"
        />
      </div>
    </div>
  );
};

export default Dashboard;
