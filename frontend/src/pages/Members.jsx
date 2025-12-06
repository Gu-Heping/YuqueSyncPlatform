import React, { useEffect, useState } from 'react';
import { getMembers, getMemberDocs } from '../api';
import { Search, User, FileText, X, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';

const MemberModal = ({ member, onClose }) => {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await getMemberDocs(member.yuque_id);
        setDocs(response.data);
      } catch (error) {
        console.error('Failed to fetch member docs:', error);
      } finally {
        setLoading(false);
      }
    };
    if (member) {
      fetchDocs();
    }
  }, [member]);

  if (!member) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose}>
      <div 
        className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative p-6 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
          <div className="flex items-center space-x-4">
            <img
              src={member.avatar_url || 'https://gw.alipayobjects.com/zos/rmsportal/BiazfanxmamNRoxxVxka.png'}
              alt={member.name}
              className="w-16 h-16 rounded-full object-cover border-2 border-white dark:border-gray-700 shadow-sm"
            />
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">{member.name}</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">@{member.login}</p>
            </div>
          </div>
          <p className="mt-3 text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
            {member.description || '暂无简介'}
          </p>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          <h4 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-4 flex items-center">
            <FileText size={14} className="mr-2" />
            贡献文档 ({docs.length})
          </h4>
          
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : docs.length > 0 ? (
            <ul className="space-y-2">
              {docs.map(doc => (
                <li key={doc.id}>
                  <Link 
                    to={`/repos/${doc.repo_id}/docs/${doc.slug}`}
                    className="group flex items-start p-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                    onClick={onClose}
                  >
                    <FileText size={16} className="mt-0.5 mr-3 text-gray-400 dark:text-gray-500 group-hover:text-blue-500 dark:group-hover:text-blue-400" />
                    <div>
                      <span className="text-sm text-gray-700 dark:text-gray-200 group-hover:text-blue-700 dark:group-hover:text-blue-300 font-medium block">
                        {doc.title}
                      </span>
                      <span className="text-xs text-gray-400 dark:text-gray-500 block mt-0.5">
                        {doc.content_updated_at || doc.updated_at 
                          ? new Date(doc.content_updated_at || doc.updated_at).toLocaleDateString() 
                          : '未知时间'} 更新
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm bg-gray-50 dark:bg-gray-900 rounded-lg border border-dashed border-gray-200 dark:border-gray-700">
              暂无文档记录
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const MemberCard = ({ member, onClick }) => {
  return (
    <div 
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all cursor-pointer group"
      onClick={() => onClick(member)}
    >
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
  );
};

const Members = () => {
  const [members, setMembers] = useState([]);
  const [filteredMembers, setFilteredMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const response = await getMembers();
        setMembers(response.data);
        setFilteredMembers(response.data);
      } catch (error) {
        console.error('Failed to fetch members:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchMembers();
  }, []);

  useEffect(() => {
    const lowerTerm = searchTerm.toLowerCase();
    const filtered = members.filter(
      (m) =>
        m.name.toLowerCase().includes(lowerTerm) ||
        m.login.toLowerCase().includes(lowerTerm)
    );
    setFilteredMembers(filtered);
  }, [searchTerm, members]);

  if (loading) return <div className="text-center py-10 dark:text-gray-300">加载中...</div>;

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 sm:mb-0">团队成员</h1>
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

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredMembers.map((member) => (
          <MemberCard 
            key={member.yuque_id} 
            member={member} 
            onClick={setSelectedMember}
          />
        ))}
      </div>

      {filteredMembers.length === 0 && (
        <div className="text-center py-12">
          <User className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-600" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">未找到成员</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">请尝试调整搜索关键词</p>
        </div>
      )}

      {/* Modal */}
      {selectedMember && (
        <MemberModal 
          member={selectedMember} 
          onClose={() => setSelectedMember(null)} 
        />
      )}
    </div>
  );
};

export default Members;
