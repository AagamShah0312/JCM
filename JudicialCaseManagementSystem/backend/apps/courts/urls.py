"""
URL routing for courts app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourtViewSet, CourtroomViewSet

router = DefaultRouter()
router.register(r'courtrooms', CourtroomViewSet, basename='courtroom')
router.register(r'', CourtViewSet, basename='court')

urlpatterns = [
    path('', include(router.urls)),
]
