"""
URL routing for cases app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseViewSet, CaseTimelineViewSet, CaseNoteViewSet

router = DefaultRouter()
router.register(r'', CaseViewSet, basename='case')
router.register(r'timeline', CaseTimelineViewSet, basename='timeline')
router.register(r'notes', CaseNoteViewSet, basename='note')

urlpatterns = [
    path('', include(router.urls)),
]
