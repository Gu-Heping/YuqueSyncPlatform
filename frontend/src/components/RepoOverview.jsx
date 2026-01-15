import React, { useEffect, useState } from 'react';
import {
    FileText,
    Users,
    Activity as ActivityIcon,
    BarChart2,
    ArrowRight,
    Search
} from 'lucide-react';
import { getMembers, getFeed, getDashboardOverview } from '../api';
import ActivityItem from './ActivityItem';

// Helper for date formatting
const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

const RepoOverview = ({ repo, onEnterDocs, onMemberClick }) => {
    const [stats, setStats] = useState(null);
    const [contributors, setContributors] = useState([]);
    const [activities, setActivities] = useState([]);

    useEffect(() => {
        const fetchData = async () => {
            // Fetch Members
            try {
                const membersRes = await getMembers({ repo_id: repo.yuque_id });
                setContributors(membersRes.data);
            } catch (error) {
                console.error('Failed to fetch members:', error);
            }

            // Fetch Stats (Dashboard)
            try {
                const statsRes = await getDashboardOverview(repo.yuque_id);
                setStats(statsRes.data);
            } catch (error) {
                console.error('Failed to fetch repo stats:', error);
            }

            // Fetch Feed (Activity)
            try {
                const feedRes = await getFeed('all', repo.yuque_id);
                setActivities(feedRes.data);
            } catch (error) {
                console.error('Failed to fetch activity feed:', error);
            }
        };

        if (repo) {
            fetchData();
        }
    }, [repo]);

    // Helper to merge adjacent activities for same doc (Copied from Home.jsx)
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


    if (!repo) return null;

    return (
        <div className="max-w-7xl mx-auto p-4 md:p-8 h-full overflow-y-auto custom-scrollbar">
            {/* Header Section */}
            <div className="mb-8 text-center md:text-left">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">{repo.name}</h1>
                <p className="text-gray-600 dark:text-gray-300 text-lg mb-6 max-w-3xl">
                    {repo.description || '暂无描述'}
                </p>
                <button
                    onClick={onEnterDocs}
                    className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-md hover:shadow-lg transform hover:-translate-y-0.5 active:translate-y-0"
                >
                    <FileText className="mr-2" size={20} />
                    进入文档阅读
                    <ArrowRight className="ml-2" size={18} />
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 pb-8">
                {/* Left Column: Stats & Contributors */}
                <div className="lg:col-span-2 space-y-8">
                    {/* Stats Cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 transition-all hover:shadow-md">
                            <div className="text-gray-500 dark:text-gray-400 text-sm mb-1 flex items-center"><FileText size={14} className="mr-1" /> 文档总数</div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_docs || '-'}</div>
                        </div>
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 transition-all hover:shadow-md">
                            <div className="text-gray-500 dark:text-gray-400 text-sm mb-1 flex items-center"><BarChart2 size={14} className="mr-1" /> 总字数</div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_words ? (stats.total_words / 10000).toFixed(1) + 'w' : '-'}</div>
                        </div>
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 transition-all hover:shadow-md">
                            <div className="text-gray-500 dark:text-gray-400 text-sm mb-1 flex items-center"><ActivityIcon size={14} className="mr-1" /> 阅读量</div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_reads || '-'}</div>
                        </div>
                        <div className="bg-white dark:bg-gray-800 p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 transition-all hover:shadow-md">
                            <div className="text-gray-500 dark:text-gray-400 text-sm mb-1 flex items-center"><ActivityIcon size={14} className="mr-1" /> 点赞数</div>
                            <div className="text-2xl font-bold text-gray-900 dark:text-white">{stats?.total_likes || '-'}</div>
                        </div>
                    </div>

                    {/* Contributors (Moved to Left) */}
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
                        <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center">
                            <Users className="mr-2 text-green-500" size={20} />
                            <h2 className="text-lg font-bold text-gray-900 dark:text-white">贡献者</h2>
                        </div>
                        <div className="p-4">
                            {contributors.length > 0 ? (
                                <div className="flex flex-wrap gap-3">
                                    {contributors.map((member) => (
                                        <div
                                            key={member.yuque_id}
                                            className="relative group w-10 h-10"
                                            onClick={() => onMemberClick && onMemberClick(member)}
                                        >
                                            <img
                                                src={member.avatar_url || `https://ui-avatars.com/api/?name=${member.name}&background=random`}
                                                alt={member.name}
                                                className="w-full h-full rounded-full border-2 border-white dark:border-gray-700 shadow-sm cursor-pointer hover:border-blue-400 transition-colors object-cover"
                                                title={member.name}
                                            />
                                            {/* Tooltip */}
                                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10 shadow-lg">
                                                {member.name}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center text-gray-500 dark:text-gray-400 py-8 bg-gray-50/50 dark:bg-gray-900/50 rounded-lg mx-2 mb-2">
                                    <Users size={32} className="mx-auto mb-2 opacity-20" />
                                    <p className="text-sm">暂无贡献者信息</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Column: Recent Activity (Moved to Right) */}
                <div className="space-y-8">
                    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden flex flex-col h-[600px] sticky top-4">
                        <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
                            <div className="flex items-center">
                                <ActivityIcon className="mr-2 text-blue-500" size={20} />
                                <h2 className="text-lg font-bold text-gray-900 dark:text-white">知识库动态</h2>
                            </div>
                        </div>
                        <div className="divide-y divide-gray-100 dark:divide-gray-700 overflow-y-auto flex-1 custom-scrollbar">
                            {activities.length > 0 ? (
                                processFeed(activities).map((activity) => (
                                    <ActivityItem key={activity.id} activity={activity} />
                                ))
                            ) : (
                                <div className="p-12 text-center text-gray-500 dark:text-gray-400 bg-gray-50/50 dark:bg-gray-900/50 h-full flex flex-col justify-center">
                                    <ActivityIcon size={48} className="mx-auto mb-3 opacity-20" />
                                    <p>最近暂无动态</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RepoOverview;
