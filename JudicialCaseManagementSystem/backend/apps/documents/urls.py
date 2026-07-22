"""
URL routing for documents app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseDocumentViewSet, DocumentVersionViewSet

router = DefaultRouter()
router.register(r'', CaseDocumentViewSet, basename='document')
router.register(r'versions', DocumentVersionViewSet, basename='document-version')

urlpatterns = [
    path('', include(router.urls)),
]
