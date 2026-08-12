"""
URL routing for cases app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseViewSet, CaseEventViewSet, CaseNoteViewSet

router = DefaultRouter()
# Register sub-resources FIRST so their routes are not shadowed by the
# empty-prefix CaseViewSet detail route (e.g. /api/cases/notes/ must reach
# CaseNoteViewSet, not CaseViewSet with pk="notes").
router.register(r'notes', CaseNoteViewSet, basename='note')
router.register(r'timeline', CaseEventViewSet, basename='timeline')
router.register(r'', CaseViewSet, basename='case')

urlpatterns = [
    path('', include(router.urls)),
]
