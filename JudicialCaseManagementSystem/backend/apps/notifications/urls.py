"""
URL routing for notifications app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationScheduleViewSet

router = DefaultRouter()
# Sub-resource first so /api/notifications/schedule/ is not shadowed by the
# empty-prefix NotificationViewSet detail route.
router.register(r'schedule', NotificationScheduleViewSet, basename='schedule')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
