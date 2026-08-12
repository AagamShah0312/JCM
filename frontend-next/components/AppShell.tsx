'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, Scale, FolderOpen, FileText, CalendarDays, Bell,
  Settings, LogOut, Menu, X, Gavel, Users, BarChart3, Search, Upload, Globe,
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { NavLink } from './ui';
import { notificationsApi } from '@/lib/services';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (user && user.role !== 'guest') {
      notificationsApi.unread().then((r) => setUnread(r.data.count)).catch(() => {});
    }
  }, [user, pathname]);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  const navItems: { href: string; label: string; icon: React.ReactNode; roles: string[] }[] = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} />, roles: ['admin', 'judge', 'lawyer'] },
    { href: '/search', label: 'Search', icon: <Search size={18} />, roles: ['admin', 'judge', 'lawyer'] },
    { href: '/cases', label: 'Cases', icon: <FolderOpen size={18} />, roles: ['admin', 'judge', 'lawyer'] },
    { href: '/cause-list', label: 'Cause List', icon: <CalendarDays size={18} />, roles: ['admin', 'judge', 'lawyer'] },
    { href: '/calendar', label: 'Calendar', icon: <CalendarDays size={18} />, roles: ['admin', 'judge', 'lawyer'] },
    { href: '/tasks', label: 'Tasks', icon: <FileText size={18} />, roles: ['admin', 'judge', 'lawyer'] },
    { href: '/admin/analytics', label: 'Analytics', icon: <BarChart3 size={18} />, roles: ['admin'] },
    { href: '/admin/csv', label: 'CSV Import', icon: <Upload size={18} />, roles: ['admin'] },
    { href: '/admin/courts', label: 'Courts & Courtrooms', icon: <Gavel size={18} />, roles: ['admin'] },
    { href: '/admin/users', label: 'Users', icon: <Users size={18} />, roles: ['admin'] },
  ];

  const visible = navItems.filter((n) => !user || n.roles.includes(user.role));

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-600 text-white">
            <Scale size={18} />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900">JCM</p>
            <p className="text-[11px] text-slate-500">Judicial Case Management</p>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}><X size={18} /></button>
        </div>
        <nav className="space-y-1 p-3">
          {visible.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <NavLink key={item.href} href={item.href} active={active}>
                {item.icon} {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>

      {sidebarOpen && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setSidebarOpen(false)} />}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-slate-200 bg-white px-4">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
          <Link href="/guest/search" className="hidden items-center gap-1 text-sm text-slate-500 hover:text-brand-600 sm:flex">
            <Search size={16} /> Public Search
          </Link>
          <div className="ml-auto flex items-center gap-3">
            {user && user.role !== 'guest' ? (
              <Link href="/notifications" className="relative text-slate-500 hover:text-slate-800">
                <Bell size={20} />
                {unread > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
                    {unread}
                  </span>
                )}
              </Link>
            ) : null}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-medium text-slate-800">{user.first_name || user.email}</p>
                  <p className="text-[11px] uppercase text-slate-400">{user.role}</p>
                </div>
                <Link href="/settings" className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800" title="Settings">
                  <Settings size={18} />
                </Link>
                <button onClick={handleLogout} className="rounded-md p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800" title="Logout">
                  <LogOut size={18} />
                </button>
              </div>
            ) : (
              <Link href="/login" className="btn-primary">Sign in</Link>
            )}
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
