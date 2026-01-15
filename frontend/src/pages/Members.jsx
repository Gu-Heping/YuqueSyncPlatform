import React, { useEffect, useState } from 'react';
import { getMembers, followMember, unfollowMember, followAllMembers, unfollowAllMembers } from '../api';
import { Search, User, UserPlus, UserMinus, Users } from 'lucide-react';
import MemberModal from '../components/MemberModal';
import { useAuth } from '../context/AuthContext';

const MemberCard = ({ member, currentUser, onFollowToggle, onClick }) => {
  const isFollowing = member.followers && currentUser && member.followers.includes(currentUser.yuque_id);
  const isSelf = currentUser && currentUser.yuque_id === member.yuque_id;

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all group relative"
    >
      <div className="absolute top-4 right-4 z-10">
        {!isSelf && currentUser && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onFollowToggle(member, isFollowing);
            }}
            className={`p-2 rounded-full transition-colors ${isFollowing
              ? 'bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400'
              : 'bg-blue-100 text-blue-600 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400'
              }`}
            title={isFollowing ? "取消关注" : "关注"}
          >
            {isFollowing ? <UserMinus size={16} /> : <UserPlus size={16} />}
          </button>
        )}
      </div>
      <div className="cursor-pointer" onClick={() => onClick(member)}>
        <div className="p-6 flex items-center space-x-4">
          <img
            src={member.avatar_url || 'https://gw.alipayobjects.com/zos/rmsportal/BiazfanxmamNRoxxVxka.png'}
            alt={member.name}
            className="w-12 h-12 rounded-full object-cover border border-gray-200 dark:border-gray-600 group-hover:border-blue-200 dark:group-hover:border-blue-800 transition-colors"
          />
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
              {member.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 truncate">@{member.login}</p>
          </div>
        </div>
        <div className="px-6 pb-4">
          <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 h-10">
            {member.description || '暂无简介'}
          </p>
        </div>
      </div>
    </div>
  );
};

const Members = () => {
  const { user } = useAuth();
  const [members, setMembers] = useState([]);
  const [filteredMembers, setFilteredMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null); // 'follow' | 'unfollow' | null
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);

  // Repo Filter
  const [repos, setRepos] = useState([]);
  const [selectedRepoId, setSelectedRepoId] = useState('');

  const fetchRepos = async () => {
    try {
      const { getRepos } = await import('../api'); // Avoid circular dependency if any
      const response = await getRepos();
      setRepos(response.data);
    } catch (error) {
      console.error('Failed to fetch repos for filtering:', error);
    }
  }

  const fetchMembers = async () => {
    try {
      setLoading(true);
      const params = selectedRepoId ? { repo_id: parseInt(selectedRepoId) } : {};

      const response = await getMembers(params);
      setMembers(response.data);
    } catch (error) {
      console.error('Failed to fetch members:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepos();
  }, []);

  useEffect(() => {
    fetchMembers();
  }, [selectedRepoId]);

  const handleFollowToggle = async (member, isFollowing) => {
    try {
      if (isFollowing) {
        await unfollowMember(member.yuque_id);
      } else {
        await followMember(member.yuque_id);
      }
      await fetchMembers();
    } catch (error) {
      console.error('Failed to toggle follow status:', error);
      // You might want to show a toast notification here
    }
  };

  const handleFollowAll = async () => {
    if (!window.confirm("确定要关注所有成员吗？")) {
      return;
    }

    try {
      setActionLoading('follow');
      await followAllMembers(selectedRepoId);
      await fetchMembers();
    } catch (error) {
      console.error('Failed to follow all members:', error);
      alert(`操作失败: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleUnfollowAll = async () => {
    if (!window.confirm("确定要取消关注所有成员吗？")) {
      return;
    }

    try {
      setActionLoading('unfollow');
      await unfollowAllMembers(selectedRepoId);
      await fetchMembers();
    } catch (error) {
      console.error('Failed to unfollow all members:', error);
      alert(`操作失败: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMemberUpdate = (updatedMember) => {
    setMembers(prev => prev.map(m => m.yuque_id === updatedMember.yuque_id ? updatedMember : m));
    if (selectedMember && selectedMember.yuque_id === updatedMember.yuque_id) {
      setSelectedMember(updatedMember);
    }
  };

  useEffect(() => {
    const lowerTerm = searchTerm.toLowerCase();
    const filtered = members.filter(
      (m) =>
        m.name.toLowerCase().includes(lowerTerm) ||
        m.login.toLowerCase().includes(lowerTerm)
    );
    setFilteredMembers(filtered);
  }, [searchTerm, members]);

  // if (loading) return <div className="text-center py-10 dark:text-gray-300">加载中...</div>;

  return (
    <div>
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-6 gap-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white sm:mb-0">团队成员</h1>

        <div className="flex flex-col sm:flex-row gap-4 w-full lg:w-auto items-center">
          {/* Repo Filter */}
          <select
            value={selectedRepoId}
            onChange={(e) => setSelectedRepoId(e.target.value)}
            className="block w-full sm:w-48 py-2 px-3 border border-gray-300 bg-white dark:bg-gray-800 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:text-gray-200 dark:border-gray-600"
          >
            <option value="">全部知识库</option>
            {repos.map(r => (
              <option key={r.yuque_id} value={r.yuque_id}>{r.name}</option>
            ))}
          </select>

          {user && (
            <div className="flex w-full sm:w-auto gap-2">
              <button
                onClick={handleFollowAll}
                disabled={actionLoading}
                className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors text-sm font-medium shadow-sm whitespace-nowrap ${actionLoading ? 'opacity-70 cursor-not-allowed' : ''
                  }`}
              >
                {actionLoading === 'follow' ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-1 sm:mr-2"></div>
                ) : (
                  <Users size={18} className="mr-1 sm:mr-2" />
                )}
                <span>一键关注所有</span>
              </button>
              <button
                onClick={handleUnfollowAll}
                disabled={actionLoading}
                className={`flex-1 sm:flex-none flex items-center justify-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors text-sm font-medium shadow-sm whitespace-nowrap ${actionLoading ? 'opacity-70 cursor-not-allowed' : ''
                  }`}
              >
                {actionLoading === 'unfollow' ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-1 sm:mr-2"></div>
                ) : (
                  <UserMinus size={18} className="mr-1 sm:mr-2" />
                )}
                <span>一键取消关注</span>
              </button>
            </div>
          )}
          <div className="relative w-full sm:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              placeholder="搜索成员..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMembers.map((member) => (
          <MemberCard
            key={member.yuque_id}
            member={member}
            currentUser={user}
            onFollowToggle={handleFollowToggle}
            onClick={setSelectedMember}
          />
        ))}
      </div>

      {
        filteredMembers.length === 0 && (
          <div className="text-center py-12">
            <User className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-600" />
            <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">未找到成员</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">请尝试调整搜索关键词</p>
          </div>
        )
      }

      {/* Modal */}
      {
        selectedMember && (
          <MemberModal
            member={selectedMember}
            onClose={() => setSelectedMember(null)}
            onUpdate={handleMemberUpdate}
          />
        )
      }
    </div >
  );
};

export default Members;
