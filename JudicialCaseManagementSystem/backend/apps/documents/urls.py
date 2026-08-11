"""
URL routing for documents app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaseDocumentViewSet, DocumentVersionViewSet

router = DefaultRouter()
# Sub-resource first so /api/documents/versions/ is not shadowed by the
# empty-prefix CaseDocumentViewSet detail route.
router.register(r'versions', DocumentVersionViewSet, basename='document-version')
router.register(r'', CaseDocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
]
