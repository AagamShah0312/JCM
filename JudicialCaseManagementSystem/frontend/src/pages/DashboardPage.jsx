/**
 * Dashboard Page
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAuthStore } from '../context/authStore';
import { casesAPI } from '../services/api';
import { FiFileText, FiCheckCircle, FiClock, FiAlertCircle } from 'react-icons/fi';
import StatCard from '../components/StatCard';
import CasesList from '../components/CasesList';
import toast from 'react-hot-toast';

const asList = (payload) => {
  if (Array.isArray(payload)) return payload;
  return payload?.results || [];
};

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [upcomingHearings, setUpcomingHearings] = useState([]);
  const [bookmarkedCases, setBookmarkedCases] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = useCallback(async () => {
    try {
      let statsData = {};

      if (user?.role === 'admin') {
        const response = await casesAPI.getStatistics();
        statsData = response.data;
      }

      const hearingsResponse = await casesAPI.getUpcomingHearings();
      setUpcomingHearings(asList(hearingsResponse.data));
      if (user?.role === 'lawyer') {
        const bookmarksResponse = await casesAPI.bookmarked();
        setBookmarkedCases(asList(bookmarksResponse.data));
      }
      setStats(statsData);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('Error loading dashboard');
      setLoading(false);
    }
  }, [user?.role]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Welcome back, {user?.first_name}!
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">Here's your case management dashboard</p>
      </div>

      {/* Stats (Admin Only) */}
      {user?.role === 'admin' && stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={FiFileText}
            label="Total Cases"
            value={stats.total_cases}
            color="blue"
          />
          <StatCard
            icon={FiCheckCircle}
            label="Active Cases"
            value={stats.active_cases}
            color="green"
          />
          <StatCard
            icon={FiAlertCircle}
            label="Closed Cases"
            value={stats.closed_cases}
            color="red"
          />
          <StatCard
            icon={FiClock}
            label="Upcoming Hearings"
            value={stats.upcoming_hearings}
            color="orange"
          />
        </div>
      )}

      {/* Upcoming Hearings */}
      {upcomingHearings.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Upcoming Hearings</h2>
          <CasesList cases={upcomingHearings} />
        </div>
      )}

      {/* Lawyer Bookmarked Cases */}
      {user?.role === 'lawyer' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Bookmarked Cases</h2>
          {bookmarkedCases.length > 0 ? (
            <CasesList cases={bookmarkedCases} />
          ) : (
            <p className="text-gray-600 dark:text-gray-300">No bookmarked cases yet</p>
          )}
        </div>
      )}

      {/* Empty State */}
      {upcomingHearings.length === 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <FiClock className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600 dark:text-gray-300">No upcoming hearings</p>
        </div>
      )}
    </div>
  );
}
