import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../context/authStore';
import { notificationsAPI } from '../services/api';
import { FiMenu, FiX, FiLogOut, FiBell, FiMoon, FiSun } from 'react-icons/fi';
import Sidebar from './Sidebar';
import NotificationPanel from './NotificationPanel';

export default function Layout({ children }) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebar_open');
    return saved === null ? true : saved === 'true';
  });
  const [showNotifications, setShowNotifications] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isDark, setIsDark] = useState(localStorage.getItem('theme') === 'dark');

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  useEffect(() => {
    localStorage.setItem('sidebar_open', String(sidebarOpen));
  }, [sidebarOpen]);

  useEffect(() => {
    fetchUnreadCount();
  }, []);

  const fetchUnreadCount = async () => {
    try {
      const response = await notificationsAPI.unread();
      setUnreadCount(response.data.count || 0);
    } catch (error) {
      setUnreadCount(0);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />

      <div className={`h-full flex flex-col overflow-hidden transition-all duration-300 ${sidebarOpen ? 'md:ml-64' : 'md:ml-0'}`}>
        <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-40 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {sidebarOpen ? <FiX size={24} /> : <FiMenu size={24} />}
            </button>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsDark((prev) => !prev)}
                className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                title="Toggle dark mode"
              >
                {isDark ? <FiSun size={18} /> : <FiMoon size={18} />}
              </button>

              <div className="relative">
                <button
                  onClick={() => setShowNotifications(!showNotifications)}
                  className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 relative"
                >
                  <FiBell size={20} />
                  {unreadCount > 0 && (
                    <span className="absolute top-1 right-1 bg-red-500 text-white text-xs rounded-full min-w-[1rem] h-4 px-1 flex items-center justify-center">
                      {unreadCount}
                    </span>
                  )}
                </button>
                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg z-50">
                    <NotificationPanel onChanged={fetchUnreadCount} />
                  </div>
                )}
              </div>

              <div className="flex items-center gap-3 pl-4 border-l border-gray-200 dark:border-gray-700">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.first_name || user?.username || 'User'}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-300">{user?.role}</p>
                </div>
                <button onClick={handleLogout} className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700" title="Logout">
                  <FiLogOut size={20} />
                </button>
              </div>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <div className="p-4 sm:p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
