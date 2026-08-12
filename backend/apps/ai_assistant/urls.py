"""
URL routing for AI assistant app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIConversationViewSet,
    AIQueryViewSet,
    CaseAIChatAPIView,
    CaseAIExplainAPIView,
    CaseAIHearingSummaryAPIView,
    CaseAIDocumentSummaryAPIView,
)

router = DefaultRouter()
router.register(r'conversations', AIConversationViewSet, basename='conversation')
router.register(r'queries', AIQueryViewSet, basename='query')

urlpatterns = [
    path('', include(router.urls)),
    path('cases/<uuid:case_id>/chat/', CaseAIChatAPIView.as_view(), name='case-ai-chat'),
    path('cases/<uuid:case_id>/explain/', CaseAIExplainAPIView.as_view(), name='case-ai-explain'),
    path('cases/<uuid:case_id>/hearing/<uuid:hearing_id>/summary/', CaseAIHearingSummaryAPIView.as_view(), name='case-ai-hearing-summary'),
    path('cases/<uuid:case_id>/documents/summary/', CaseAIDocumentSummaryAPIView.as_view(), name='case-ai-documents-summary'),
]
