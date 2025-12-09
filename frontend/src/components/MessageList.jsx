import React from 'react';
import { MessageSquare, User } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDate } from '../utils/date';

const MessageList = ({ comments }) => {
  if (!comments || comments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <MessageSquare className="w-12 h-12 mb-2 opacity-20" />
        <p>暂无评论</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {comments.map((comment) => (
        <div key={comment.yuque_id} className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              {comment.user && comment.user.avatar_url ? (
                <img 
                  src={comment.user.avatar_url} 
                  alt={comment.user.name} 
                  className="w-8 h-8 rounded-full object-cover"
                />
              ) : (
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {comment.user ? comment.user.name : `用户 ${comment.user_id}`}
                  </span>
                  {comment.doc_title && (
                    <span className="text-xs text-gray-500">
                      评论了文档 <Link to={`/repos/${comment.repo_id}/docs/${comment.doc_slug}`} className="text-blue-500 hover:underline">{comment.doc_title}</Link>
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatDate(comment.created_at, { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </p>
              </div>
              <div 
                className="mt-1 text-sm text-gray-700 dark:text-gray-300 prose dark:prose-invert max-w-none"
                dangerouslySetInnerHTML={{ __html: comment.body_html }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageList;
