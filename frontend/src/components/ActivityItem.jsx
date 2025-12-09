import React from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { FileText, Edit, PlusCircle, MessageSquare } from 'lucide-react';

const ActivityItem = ({ activity }) => {
  const isPublish = activity.action_type === 'publish';
  const isComment = ['comment_create', 'comment_reply_create'].includes(activity.action_type);
  
  // 修复时间显示问题：后端返回的是 UTC 时间但可能没有 Z 后缀，导致前端按本地时间解析
  const getDate = (dateString) => {
    if (!dateString) return new Date();
    // 如果是字符串且不包含时区信息（Z 或 +），则手动添加 Z 视为 UTC
    if (typeof dateString === 'string' && !dateString.endsWith('Z') && !dateString.includes('+')) {
      return new Date(dateString + 'Z');
    }
    return new Date(dateString);
  };

  let actionText = '更新了文档';
  if (isPublish) actionText = '发布了文档';
  if (isComment) actionText = '评论了文档';

  return (
    <div className="flex items-start p-4 bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
      {/* Avatar */}
      <div className="flex-shrink-0 mr-4">
        <img
          src={activity.author_avatar || 'https://gw.alipayobjects.com/zos/rmsportal/BiazfanxmamNRoxxVxka.png'}
          alt={activity.author_name}
          className="w-10 h-10 rounded-full object-cover border border-gray-200 dark:border-gray-600"
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="text-sm text-gray-900 dark:text-gray-100">
            <span className="font-semibold mr-1">{activity.author_name}</span>
            <span className="text-gray-500 dark:text-gray-400">
              {actionText}
            </span>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap ml-2">
            {formatDistanceToNow(getDate(activity.created_at), { addSuffix: true, locale: zhCN })}
          </span>
        </div>

        {/* Doc Card */}
        <Link 
          to={`/repos/${activity.repo_id}/docs/${activity.doc_slug}`}
          className="block mt-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 transition-colors group"
        >
           {/* I will assume I will fix the backend to include repo_id and slug */}
           <div className="flex items-center mb-1">
             {isPublish && <PlusCircle size={14} className="text-green-500 mr-2" />}
             {activity.action_type === 'update' && <Edit size={14} className="text-blue-500 mr-2" />}
             {isComment && <MessageSquare size={14} className="text-purple-500 mr-2" />}
             
             <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
               {activity.doc_title}
             </h4>
           </div>
           <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
             {activity.summary || '暂无摘要'}
           </p>
           <div className="mt-2 flex items-center text-xs text-gray-400 dark:text-gray-500">
             <FileText size={12} className="mr-1" />
             <span>{activity.repo_name}</span>
           </div>
        </Link>
      </div>
    </div>
  );
};

export default ActivityItem;
