"""
URL routing for analytics app
"""
from django.urls import path
from .views import (
    AdminAnalyticsView, CauseListView, CalendarEventsView,
    CaseHealthView, WhatChangedView, SmartSchedulingView,
)

urlpatterns = [
    path('admin/', AdminAnalyticsView.as_view(), name='admin-analytics'),
    path('cause-list/', CauseListView.as_view(), name='cause-list'),
    path('calendar/', CalendarEventsView.as_view(), name='calendar-events'),
    path('cases/<uuid:case_id>/health/', CaseHealthView.as_view(), name='case-health'),
    path('cases/<uuid:case_id>/what-changed/', WhatChangedView.as_view(), name='what-changed'),
    path('cases/<uuid:case_id>/scheduling-suggestions/', SmartSchedulingView.as_view(), name='smart-scheduling'),
]
