import React, { useState, useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import { getComments, markCommentsRead } from '../api';
import MessageList from '../components/MessageList';

const MessagesPage = () => {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchComments = async () => {
      try {
        // 默认只显示与我相关的评论
        const res = await getComments({ limit: 50, filter_type: 'me' });
        setComments(res.data);
        // Mark as read when viewing the page
        await markCommentsRead();
      } catch (error) {
        console.error("Failed to fetch comments", error);
      } finally {
        setLoading(false);
      }
    };
    fetchComments();
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center mb-6">
        <MessageSquare className="w-6 h-6 text-blue-500 mr-2" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">消息通知</h1>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64 text-gray-500">
          加载中...
        </div>
      ) : (
        <MessageList comments={comments} />
      )}
    </div>
  );
};

export default MessagesPage;
