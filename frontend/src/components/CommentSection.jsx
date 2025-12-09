import React, { useState, useEffect, useMemo } from 'react';
import { fetchDocComments } from '../api';
import DOMPurify from 'dompurify';
import { formatDate } from '../utils/date';

const CommentItem = ({ comment, childrenComments }) => {
  return (
    <div className="flex space-x-4">
      <div className="flex-shrink-0">
        {comment.user.avatar_url ? (
          <img
            className="h-10 w-10 rounded-full"
            src={comment.user.avatar_url}
            alt={comment.user.name}
          />
        ) : (
          <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-500">
            {comment.user.name[0]}
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-200">
            {comment.user.name}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {formatDate(comment.created_at, { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </p>
        </div>
        <div 
          className="mt-1 text-sm text-gray-700 dark:text-gray-300 prose prose-sm max-w-none dark:prose-invert"
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(comment.body_html || comment.body)
          }}
        />
        
        {/* Render children (replies) */}
        {childrenComments && childrenComments.length > 0 && (
          <div className="mt-4 space-y-4 pl-4 border-l-2 border-gray-100 dark:border-gray-700">
            {childrenComments.map(child => (
              <CommentItem 
                key={child.yuque_id} 
                comment={child} 
                childrenComments={child.children} 
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const CommentSection = ({ docId }) => {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (docId) {
      loadComments();
    }
  }, [docId]);

  const loadComments = async () => {
    setLoading(true);
    try {
      const response = await fetchDocComments(docId);
      setComments(response.data);
    } catch (error) {
      console.error("Failed to load comments:", error);
    } finally {
      setLoading(false);
    }
  };

  // Build comment tree
  const commentTree = useMemo(() => {
    if (!comments || comments.length === 0) return [];
    
    const commentMap = {};
    const roots = [];

    // First pass: create map and initialize children array
    comments.forEach(c => {
      commentMap[c.yuque_id] = { ...c, children: [] };
    });

    // Second pass: link children to parents
    comments.forEach(c => {
      if (c.parent_id && commentMap[c.parent_id]) {
        commentMap[c.parent_id].children.push(commentMap[c.yuque_id]);
      } else {
        roots.push(commentMap[c.yuque_id]);
      }
    });

    // Sort by created_at (oldest first for comments usually, or newest first? 
    // Yuque usually shows oldest first for conversation flow, but let's stick to API sort which is newest first)
    // If API returns newest first, then roots are newest first.
    // For replies, usually we want oldest first? Let's keep it simple and respect API order for now.
    
    return roots;
  }, [comments]);

  if (loading) {
    return <div className="text-gray-500 text-sm py-4">加载评论中...</div>;
  }

  if (!comments || comments.length === 0) {
    return (
      <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">评论</h3>
        <div className="text-gray-400 text-sm">暂无评论</div>
      </div>
    );
  }

  return (
    <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold mb-6 text-gray-900 dark:text-gray-100">评论 ({comments.length})</h3>
      <div className="space-y-6">
        {commentTree.map((comment) => (
          <CommentItem 
            key={comment.yuque_id} 
            comment={comment} 
            childrenComments={comment.children} 
          />
        ))}
      </div>
    </div>
  );
};

export default CommentSection;
