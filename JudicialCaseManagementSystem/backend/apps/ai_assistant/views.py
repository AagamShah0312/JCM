"""
Views for AI assistant app
"""
from django.core.cache import cache
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied
import time
import logging

from .models import AIConversation, AIMessage, AIQuery
from .serializers import (
    AIConversationSerializer, AIMessageSerializer, 
    AIMessageCreateSerializer, AIQuerySerializer
)
from .services import RAGService, DocumentProcessor
from apps.cases.models import Case
from apps.cases.permissions import can_view_case
from django.db.models import Q
from apps.documents.models import CaseDocument
from apps.ai import services as ai_services

logger = logging.getLogger(__name__)


def _can_access_case_ai(user, case):
    return can_view_case(user, case)


def _conversation_history(conversation, limit=10):
    messages = list(
        conversation.messages.order_by('-created_at').values('role', 'content')[:limit]
    )
    return list(reversed(messages))


def _conversation_payload(conversation):
    return AIConversationSerializer(conversation).data


def _case_sources(case):
    documents = (
        CaseDocument.objects.filter(case=case)
        .select_related('extraction')
        .order_by('-uploaded_at')
    )
    sources = []
    for doc in documents[:5]:
        sources.append({
            'doc_id': str(doc.id),
            'file_name': doc.file_name,
            'document_type': doc.document_type,
            'file_url': getattr(doc.file, 'url', ''),
        })
    return sources


class CaseAssistantMixin:
    """Shared helpers for case-aware AI endpoints."""

    def get_case(self, case_id):
        return get_object_or_404(Case, id=case_id)

    def get_conversation(self, case, user):
        conversation, _ = AIConversation.objects.get_or_create(
            case=case,
            user=user,
            defaults={'title': f"{case.case_number} AI Assistant"},
        )
        return conversation

    def serialize_messages(self, conversation):
        return AIMessageSerializer(conversation.messages.all(), many=True).data

    def ensure_access(self, user, case):
        if not _can_access_case_ai(user, case):
            raise PermissionDenied("You are not assigned to this case")

    def log_query(self, *, user, case, query_type, query_text, response, tokens_used, processing_time, success, error_message=''):
        AIQuery.objects.create(
            user=user,
            case=case,
            query_type=query_type,
            query_text=query_text,
            response=response,
            tokens_used=tokens_used,
            processing_time=processing_time,
            success=success,
            error_message=error_message,
        )

    def _store_citations(self, message, citations):
        """Persist structured citations against an assistant message."""
        from .models import AICitation
        if not citations:
            return
        for cit in citations:
            AICitation.objects.create(
                message=message,
                source_type=cit.get('source_type', 'other'),
                source_id=cit.get('source_id'),
                source_label=cit.get('source_label', ''),
                page_number=cit.get('page_number'),
                chunk_index=cit.get('chunk_index'),
                excerpt=cit.get('excerpt', ''),
                url=cit.get('url', ''),
                metadata=cit.get('metadata', {}),
            )


class CaseAIChatAPIView(CaseAssistantMixin, APIView):
    """Chat with AI about the currently selected case."""

    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = self.get_case(case_id)
        self.ensure_access(request.user, case)
        conversation = self.get_conversation(case, request.user)
        return Response({
            'case': {
                'id': str(case.id),
                'case_number': case.case_number,
                'title': case.title,
            },
            'conversation': _conversation_payload(conversation),
            'messages': self.serialize_messages(conversation),
        })

    def post(self, request, case_id):
        case = self.get_case(case_id)
        self.ensure_access(request.user, case)

        serializer = AIMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = self.get_conversation(case, request.user)
        user_message_text = serializer.validated_data['content']
        history = _conversation_history(conversation)
        user_message = AIMessage.objects.create(
            conversation=conversation,
            role='user',
            content=user_message_text,
        )

        # Structured, permission-filtered answer with citations (apps.ai)
        start_time = time.time()
        structured = ai_services.answer_case_question(request.user, case, user_message_text, history=history)
        processing_time = time.time() - start_time

        if structured.get('success'):
            assistant_message = AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=structured.get('answer', ''),
                tokens_used=0,
                sources=structured.get('sources', []),
            )
            self._store_citations(assistant_message, structured.get('citations', []))
            self.log_query(
                user=request.user,
                case=case,
                query_type='qa',
                query_text=user_message_text,
                response=structured.get('answer', ''),
                tokens_used=0,
                processing_time=processing_time,
                success=True,
            )
        else:
            assistant_message = AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=structured.get('answer') or f"Error: {structured.get('error', 'Unknown error')}",
            )
            self.log_query(
                user=request.user,
                case=case,
                query_type='qa',
                query_text=user_message_text,
                response=assistant_message.content,
                tokens_used=0,
                processing_time=processing_time,
                success=False,
                error_message=structured.get('error', ''),
            )

        conversation.save(update_fields=['updated_at'])
        return Response({
            'case': {
                'id': str(case.id),
                'case_number': case.case_number,
                'title': case.title,
            },
            'conversation': _conversation_payload(conversation),
            'user_message': AIMessageSerializer(user_message).data,
            'assistant_message': AIMessageSerializer(assistant_message).data,
            'messages': self.serialize_messages(conversation),
            'sources': structured.get('sources', []),
            'citations': structured.get('citations', []),
            'warnings': structured.get('warnings', []),
        }, status=status.HTTP_201_CREATED)


class CaseAIExplainAPIView(CaseAssistantMixin, APIView):
    """Generate and cache a simplified explanation for a case."""

    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = self.get_case(case_id)
        self.ensure_access(request.user, case)

        latest_document = (
            CaseDocument.objects.filter(case=case).order_by('-updated_at').values('updated_at').first()
        )
        document_signature = latest_document['updated_at'].isoformat() if latest_document and latest_document['updated_at'] else 'no-docs'
        cache_key = f'case-ai-explanation:{case.id}:{case.updated_at.isoformat()}:{document_signature}'
        cached = cache.get(cache_key)
        if cached:
            return Response({**cached, 'cached': True})

        start_time = time.time()
        structured = ai_services.summarize_case(request.user, case, summary_type='case')
        processing_time = time.time() - start_time
        if structured.get('success'):
            payload = {
                'case': {
                    'id': str(case.id),
                    'case_number': case.case_number,
                    'title': case.title,
                    'status': case.status,
                },
                'explanation': structured.get('summary', ''),
                'sources': structured.get('citations', []),
                'citations': structured.get('citations', []),
                'warnings': structured.get('warnings', []),
                'generated_at': timezone.now().isoformat(),
                'processing_time': processing_time,
                'cached': False,
            }
            cache.set(cache_key, payload, 6 * 60 * 60)
            self.log_query(
                user=request.user,
                case=case,
                query_type='explain',
                query_text='Explain this case',
                response=structured.get('summary', ''),
                tokens_used=0,
                processing_time=processing_time,
                success=True,
            )
            return Response(payload)

        return Response({
            'error': structured.get('error', 'Failed to generate explanation'),
        }, status=status.HTTP_400_BAD_REQUEST)


class AIConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for AI conversations"""
    
    serializer_class = AIConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return AIConversation.objects.all().order_by('-updated_at')
        if user.role == 'guest':
            return AIConversation.objects.filter(user=user).order_by('-updated_at')
        if user.role == 'judge':
            return AIConversation.objects.filter(
                Q(user=user),
                Q(case__assigned_judge=user) | Q(case__created_by=user)
            ).distinct().order_by('-updated_at')
        return AIConversation.objects.filter(
            Q(user=user),
            Q(case__assigned_lawyer=user) | Q(case__assignments__lawyer=user)
        ).distinct().order_by('-updated_at')
    
    def perform_create(self, serializer):
        case = serializer.validated_data['case']
        user = self.request.user
        if user.role != 'admin':
            is_assigned = (
                case.assigned_lawyer_id == user.id or
                case.assignments.filter(lawyer=user).exists() or
                case.assigned_judge_id == user.id or
                case.created_by_id == user.id or
                user.role == 'guest'
            )
            if not is_assigned:
                raise PermissionDenied("You are not assigned to this case")
        serializer.save(user=user)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send message to AI assistant"""
        conversation = self.get_object()
        serializer = AIMessageCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            user_message_text = serializer.validated_data['content']
            history = _conversation_history(conversation)
            
            # Save user message
            user_message = AIMessage.objects.create(
                conversation=conversation,
                role='user',
                content=user_message_text
            )
            
            # Generate AI response using the case-aware prompt builder
            rag_service = RAGService()
            start_time = time.time()
            
            ai_response = rag_service.query_case(
                str(conversation.case.id),
                user_message_text,
                history=history,
            )
            processing_time = time.time() - start_time
            
            # Save AI response
            if ai_response.get('success'):
                assistant_message = AIMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=ai_response.get('response', ''),
                    tokens_used=ai_response.get('tokens_used', 0),
                    sources=ai_response.get('sources', [])
                )
                
                # Log query
                AIQuery.objects.create(
                    user=request.user,
                    case=conversation.case,
                    query_type='qa',
                    query_text=user_message_text,
                    response=ai_response.get('response', ''),
                    tokens_used=ai_response.get('tokens_used', 0),
                    processing_time=processing_time,
                    success=True
                )
            else:
                error_response = f"Error: {ai_response.get('error', 'Unknown error')}"
                assistant_message = AIMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=error_response
                )
                
                AIQuery.objects.create(
                    user=request.user,
                    case=conversation.case,
                    query_type='qa',
                    query_text=user_message_text,
                    response=error_response,
                    processing_time=processing_time,
                    success=False,
                    error_message=ai_response.get('error', '')
                )
            
            conversation.save()  # Update updated_at
            
            messages = AIMessage.objects.filter(conversation=conversation)
            messages_serializer = AIMessageSerializer(messages, many=True)
            
            return Response({
                'conversation': AIConversationSerializer(conversation).data,
                'messages': messages_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def summarize(self, request, pk=None):
        """Generate case summary"""
        conversation = self.get_object()
        
        try:
            rag_service = RAGService()
            start_time = time.time()
            
            result = rag_service.summarize_case(str(conversation.case.id))
            processing_time = time.time() - start_time
            
            if result.get('success'):
                summary_text = result.get('summary', '')
                
                # Create AI message with summary
                summary_message = AIMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=summary_text,
                    tokens_used=result.get('tokens_used', 0)
                )
                
                AIQuery.objects.create(
                    user=request.user,
                    case=conversation.case,
                    query_type='summarize',
                    query_text='Summarize this case',
                    response=summary_text,
                    tokens_used=result.get('tokens_used', 0),
                    processing_time=processing_time,
                    success=True
                )
                
                return Response({
                    'summary': summary_text,
                    'tokens_used': result.get('tokens_used', 0),
                    'processing_time': processing_time
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to generate summary')
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error in summarize: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def generate_timeline(self, request, pk=None):
        """Generate case timeline"""
        conversation = self.get_object()
        
        try:
            rag_service = RAGService()
            start_time = time.time()
            
            result = rag_service.generate_timeline(str(conversation.case.id))
            processing_time = time.time() - start_time
            
            if result.get('success'):
                timeline = result.get('timeline', [])
                
                AIQuery.objects.create(
                    user=request.user,
                    case=conversation.case,
                    query_type='timeline',
                    query_text='Generate timeline',
                    response=str(timeline),
                    tokens_used=result.get('tokens_used', 0),
                    processing_time=processing_time,
                    success=True
                )
                
                return Response({
                    'timeline': timeline,
                    'tokens_used': result.get('tokens_used', 0),
                    'processing_time': processing_time
                })
            else:
                return Response({
                    'error': result.get('error', 'Failed to generate timeline')
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Error in generate_timeline: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class AIQueryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AI query history"""
    
    serializer_class = AIQuerySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case', 'query_type', 'success']
    
    def get_queryset(self):
        return AIQuery.objects.filter(user=self.request.user).order_by('-created_at')
