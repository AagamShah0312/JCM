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
)

router = DefaultRouter()
router.register(r'conversations', AIConversationViewSet, basename='conversation')
router.register(r'queries', AIQueryViewSet, basename='query')

urlpatterns = [
    path('', include(router.urls)),
    path('cases/<uuid:case_id>/chat/', CaseAIChatAPIView.as_view(), name='case-ai-chat'),
    path('cases/<uuid:case_id>/explain/', CaseAIExplainAPIView.as_view(), name='case-ai-explain'),
]
