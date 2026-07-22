"""
URL routing for notifications app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationScheduleViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')
router.register(r'schedule', NotificationScheduleViewSet, basename='schedule')

urlpatterns = [
    path('', include(router.urls)),
]
