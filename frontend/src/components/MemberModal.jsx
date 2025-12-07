import React, { useEffect, useState } from 'react';
import { getMemberDocs } from '../api';
import { FileText, X, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '../utils/date';

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
                        {formatDate(doc.content_updated_at || doc.updated_at)} 更新
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

export default MemberModal;
