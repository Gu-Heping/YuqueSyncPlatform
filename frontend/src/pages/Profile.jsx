import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getMembers } from '../api';
import { User, Mail, Lock, Save, Users } from 'lucide-react';

const Profile = () => {
  const { user, updateProfile } = useAuth();
  const [members, setMembers] = useState([]);
  const [email, setEmail] = useState(user?.email || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const response = await getMembers();
        setMembers(response.data);
      } catch (error) {
        console.error('Failed to fetch members', error);
      }
    };
    fetchMembers();
  }, []);

  const handleUpdate = async (e) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });

    if (password && password !== confirmPassword) {
      setMessage({ type: 'error', text: '两次输入的密码不一致' });
      return;
    }

    try {
      const data = {};
      if (email !== user.email) data.email = email;
      if (password) data.password = password;

      if (Object.keys(data).length === 0) return;

      await updateProfile(data);
      setMessage({ type: 'success', text: '个人信息更新成功' });
      setPassword('');
      setConfirmPassword('');
    } catch (error) {
      setMessage({ type: 'error', text: '更新失败，请重试' });
    }
  };

  if (!user) return null;

  // Find current user in the fresh members list to get up-to-date followers
  const currentUserInMembers = members.find(m => m.yuque_id === user.yuque_id);
  const myFollowersIds = currentUserInMembers ? currentUserInMembers.followers : (user.followers || []);

  const followingList = members.filter(m => m.followers && m.followers.includes(user.yuque_id));
  const followersList = members.filter(m => myFollowersIds && myFollowersIds.includes(m.yuque_id));

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6 flex items-center">
          <img 
            className="h-16 w-16 rounded-full mr-4" 
            src={user.avatar_url} 
            alt={user.name} 
          />
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
              {user.name}
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500 dark:text-gray-400">
              @{user.login}
            </p>
          </div>
        </div>
        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-5 sm:p-0">
          <form onSubmit={handleUpdate} className="p-6 space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                绑定邮箱
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="email"
                  className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 sm:text-sm border-gray-300 rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
              <h4 className="text-md font-medium text-gray-900 dark:text-white mb-4">修改密码</h4>
              <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-3">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    新密码
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="password"
                      className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 sm:text-sm border-gray-300 rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                </div>

                <div className="sm:col-span-3">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    确认新密码
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="password"
                      className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 sm:text-sm border-gray-300 rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
              <h4 className="text-md font-medium text-gray-900 dark:text-white mb-4 flex items-center">
                <Users className="h-5 w-5 mr-2" />
                社交关系
              </h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h5 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                    我关注的人 ({followingList.length})
                  </h5>
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-md p-4 max-h-60 overflow-y-auto">
                    {followingList.length > 0 ? (
                      <ul className="space-y-3">
                        {followingList.map(m => (
                          <li key={m.yuque_id} className="flex items-center space-x-3">
                            <img src={m.avatar_url} alt={m.name} className="w-8 h-8 rounded-full" />
                            <span className="text-sm text-gray-900 dark:text-white">{m.name}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-500">暂无关注</p>
                    )}
                  </div>
                </div>

                <div>
                  <h5 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                    关注我的人 ({followersList.length})
                  </h5>
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-md p-4 max-h-60 overflow-y-auto">
                    {followersList.length > 0 ? (
                      <ul className="space-y-3">
                        {followersList.map(m => (
                          <li key={m.yuque_id} className="flex items-center space-x-3">
                            <img src={m.avatar_url} alt={m.name} className="w-8 h-8 rounded-full" />
                            <span className="text-sm text-gray-900 dark:text-white">{m.name}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-500">暂无粉丝</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {message.text && (
              <div className={`p-4 rounded-md ${message.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                {message.text}
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Save className="w-4 h-4 mr-2" />
                保存更改
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Profile;
