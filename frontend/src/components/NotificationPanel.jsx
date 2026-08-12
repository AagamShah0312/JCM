/**
 * Notification Panel Component
 */
import React, { useState, useEffect } from 'react';
import { notificationsAPI } from '../services/api';
import { FiCheckCircle, FiAlertCircle, FiInfo } from 'react-icons/fi';
import toast from 'react-hot-toast';

export default function NotificationPanel({ onChanged }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await notificationsAPI.unread();
      setNotifications(response.data.notifications);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (id) => {
    try {
      await notificationsAPI.markAsRead(id);
      setNotifications(notifications.filter((n) => n.id !== id));
      if (onChanged) onChanged();
      toast.success('Notification marked as read');
    } catch (error) {
      toast.error('Error marking notification as read');
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'case_assigned':
        return <FiAlertCircle className="text-blue-500" />;
      case 'hearing_scheduled':
        return <FiAlertCircle className="text-orange-500" />;
      case 'document_uploaded':
        return <FiCheckCircle className="text-green-500" />;
      default:
        return <FiInfo className="text-gray-500" />;
    }
  };

  return (
    <div className="p-4">
      <h3 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">Notifications</h3>
      {loading ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Loading...</p>
      ) : notifications.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No notifications</p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className="rounded-lg border border-slate-200 bg-slate-50 p-3 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800"
            >
              <div className="flex items-start gap-2">
                <div className="mt-1">{getIcon(notification.notification_type)}</div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{notification.title}</p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{notification.message}</p>
                </div>
                <button
                  onClick={() => handleMarkAsRead(notification.id)}
                  className="whitespace-nowrap text-xs text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-200"
                >
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
