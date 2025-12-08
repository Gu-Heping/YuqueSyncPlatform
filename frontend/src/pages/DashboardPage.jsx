import React, { useEffect, useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area, Legend 
} from 'recharts';
import { 
  FileText, Users, BookOpen, Heart, TrendingUp, Award, 
  Activity, Calendar 
} from 'lucide-react';
import { getDashboardOverview, getDashboardTrends, getDashboardRankings } from '../api';
import { format, parseISO } from 'date-fns';

const StatCard = ({ title, value, icon: Icon, color }) => (
  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex items-center">
    <div className={`p-4 rounded-full mr-4 ${color}`}>
      <Icon className="w-6 h-6 text-white" />
    </div>
    <div>
      <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{title}</p>
      <h3 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value}</h3>
    </div>
  </div>
);

const RankingList = ({ title, data, icon: Icon, valueLabel }) => (
  <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 h-full">
    <div className="flex items-center mb-6">
      <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg mr-3">
        <Icon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
      </div>
      <h3 className="text-lg font-bold text-gray-900 dark:text-white">{title}</h3>
    </div>
    <div className="space-y-4">
      {data.map((item, index) => (
        <div key={item.user_id} className="flex items-center justify-between group">
          <div className="flex items-center flex-1 min-w-0">
            <span className={`
              w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold mr-3 shrink-0
              ${index < 3 
                ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' 
                : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}
            `}>
              {index + 1}
            </span>
            <img 
              src={item.avatar_url} 
              alt={item.name} 
              className="w-8 h-8 rounded-full mr-3 border border-gray-200 dark:border-gray-700"
            />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              {item.name}
            </span>
          </div>
          <span className="text-sm font-semibold text-gray-900 dark:text-white ml-2 shrink-0">
            {typeof item.value === 'number' && item.value > 10000 
              ? `${(item.value / 10000).toFixed(1)}w` 
              : item.value} 
            <span className="text-xs text-gray-400 font-normal ml-1">{valueLabel}</span>
          </span>
        </div>
      ))}
      {data.length === 0 && (
        <div className="text-center text-gray-400 py-8 text-sm">暂无数据</div>
      )}
    </div>
  </div>
);

const DashboardPage = () => {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState([]);
  const [rankings, setRankings] = useState({ word_rank: [], likes_rank: [], read_rank: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [overviewRes, trendsRes, rankingsRes] = await Promise.all([
          getDashboardOverview(),
          getDashboardTrends(30),
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
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">数据看板</h1>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          数据更新于 {format(new Date(), 'yyyy-MM-dd HH:mm')}
        </span>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="文档总数" 
          value={overview?.total_docs || 0} 
          icon={FileText} 
          color="bg-blue-500" 
        />
        <StatCard 
          title="累计字数" 
          value={overview?.total_words ? `${(overview.total_words / 10000).toFixed(1)}w` : 0} 
          icon={BookOpen} 
          color="bg-green-500" 
        />
        <StatCard 
          title="总阅读量" 
          value={overview?.total_reads || 0} 
          icon={Users} 
          color="bg-purple-500" 
        />
        <StatCard 
          title="今日活跃用户" 
          value={overview?.today_active_users || 0} 
          icon={Activity} 
          color="bg-orange-500" 
        />
      </div>

      {/* Trend Chart */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center mb-6">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg mr-3">
            <TrendingUp className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">近30天趋势分析</h3>
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
                tickFormatter={(str) => format(parseISO(str), 'MM-dd')}
                stroke="#9CA3AF"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis 
                stroke="#9CA3AF"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" className="dark:stroke-gray-700" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.9)', 
                  borderRadius: '8px', 
                  border: 'none', 
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' 
                }}
                labelStyle={{ color: '#374151', fontWeight: 'bold', marginBottom: '4px' }}
              />
              <Legend iconType="circle" />
              <Area 
                type="monotone" 
                dataKey="new_docs" 
                name="新增文档" 
                stroke="#3B82F6" 
                fillOpacity={1} 
                fill="url(#colorDocs)" 
                strokeWidth={2}
              />
              <Area 
                type="monotone" 
                dataKey="active_users" 
                name="活跃人数" 
                stroke="#10B981" 
                fillOpacity={1} 
                fill="url(#colorUsers)" 
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Rankings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <RankingList 
          title="笔耕不辍榜" 
          data={rankings.word_rank} 
          icon={Award} 
          valueLabel="字"
        />
        <RankingList 
          title="人气之星榜" 
          data={rankings.likes_rank} 
          icon={Heart} 
          valueLabel="赞"
        />
        <RankingList 
          title="知识传播榜" 
          data={rankings.read_rank} 
          icon={BookOpen} 
          valueLabel="阅"
        />
      </div>
    </div>
  );
};

export default DashboardPage;
