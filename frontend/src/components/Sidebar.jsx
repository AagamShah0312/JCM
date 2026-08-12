import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../context/authStore';
import { FiHome, FiFileText, FiSearch, FiCpu, FiSettings, FiUsers, FiBarChart2 } from 'react-icons/fi';

const menuItems = [
  { icon: FiHome, label: 'Dashboard', path: '/', roles: ['admin', 'judge', 'lawyer', 'guest'] },
  { icon: FiFileText, label: 'Cases', path: '/cases', roles: ['admin', 'judge', 'lawyer', 'guest'] },
  { icon: FiSearch, label: 'Search', path: '/search', roles: ['admin', 'judge', 'lawyer', 'guest'] },
  { icon: FiCpu, label: 'AI Assistant', path: '/ai', roles: ['admin', 'judge', 'lawyer', 'guest'] },
  { icon: FiUsers, label: 'Staff Admin', path: '/staff', roles: ['admin'] },
  { icon: FiBarChart2, label: 'Analytics', path: '/analytics', roles: ['admin', 'judge', 'lawyer', 'guest'] },
  { icon: FiSettings, label: 'Settings', path: '/settings', roles: ['admin', 'judge', 'lawyer', 'guest'] },
];

export default function Sidebar({ open, setOpen }) {
  const location = useLocation();
  const { user } = useAuthStore();
  const filteredMenuItems = menuItems.filter((item) => item.roles.includes(user?.role));

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform bg-white shadow-lg transition-transform duration-300 dark:bg-slate-900 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center justify-center border-b border-slate-200 dark:border-slate-700">
            <h1 className="text-2xl font-bold text-blue-600">JCM</h1>
          </div>

          <nav className="flex-1 space-y-2 px-2 py-4">
            {filteredMenuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setOpen(false)}
                  className={`flex items-center gap-3 rounded-lg px-4 py-3 transition-colors ${
                    isActive
                      ? 'bg-blue-50 font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
                      : 'text-slate-600 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon size={20} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-slate-200 p-4 dark:border-slate-700">
            <p className="text-center text-xs text-slate-500 dark:text-slate-400">
              Copyright 2026 Judicial Case Management System
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
