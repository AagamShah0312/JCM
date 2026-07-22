"""
Views for cases app
"""
from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q
from .models import Case, CaseTimeline, CaseAssignment, CaseNote
from .serializers import (
    CaseDetailSerializer, CaseListSerializer, CaseTimelineSerializer,
    CaseAssignmentSerializer, CaseNoteSerializer, CaseUpdateSerializer, CaseCreateSerializer
)
from .permissions import IsAdminOrReadOnly, IsLawyerOrAdmin
import logging

logger = logging.getLogger(__name__)


class CaseViewSet(viewsets.ModelViewSet):
    """ViewSet for case management"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'court_name', 'case_type', 'filing_date']
    search_fields = ['case_number', 'title', 'plaintiff_name', 'defendant_name', 'judge_name']
    ordering_fields = ['created_at', 'filing_date', 'next_hearing_date', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter cases based on user role"""
        if self.request.user.role in ['admin', 'guest']:
            return Case.objects.all()
        if self.request.user.role == 'judge':
            return Case.objects.filter(Q(assigned_judge=self.request.user) | Q(created_by=self.request.user)).distinct()
        # Lawyers can browse all cases; bookmarks/assignments are personal.
        return Case.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CaseDetailSerializer
        elif self.action == 'create':
            return CaseCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return CaseUpdateSerializer
        return CaseListSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        if self.request.user.role not in ['admin', 'judge']:
            raise PermissionDenied("Only admins and judges can create cases")
        case = serializer.save(created_by=self.request.user)
        if self.request.user.role == 'judge' and not case.assigned_judge_id:
            case.assigned_judge = self.request.user
            case.judge_name = case.judge_name or self.request.user.get_full_name() or self.request.user.email
            case.save(update_fields=['assigned_judge', 'judge_name', 'updated_at'])
        if case.next_hearing_date:
            self._create_hearing_event(case, case.next_hearing_date)

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['admin', 'judge']:
            return Response({'error': 'Only admins and judges can create cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        case = self.get_object()
        if not self._can_write_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can update cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        case = self.get_object()
        if not self._can_write_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can update cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can delete cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """Log case updates"""
        old_next_hearing_date = serializer.instance.next_hearing_date
        instance = serializer.save()
        if old_next_hearing_date != instance.next_hearing_date:
            self._adjust_latest_hearing_event(instance, old_next_hearing_date, instance.next_hearing_date)
        logger.info(f"Case {instance.case_number} updated by {self.request.user.email}")
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get case timeline"""
        case = self.get_object()
        events = case.timeline_events.all()
        serializer = CaseTimelineSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_timeline_event(self, request, pk=None):
        """Add a timeline event to a case"""
        case = self.get_object()
        serializer = CaseTimelineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(case=case, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'post'])
    def notes(self, request, pk=None):
        """Get or add notes to a case"""
        case = self.get_object()
        
        if request.method == 'POST':
            serializer = CaseNoteSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(case=case, author=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        notes = case.notes.all()
        serializer = CaseNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_lawyer(self, request, pk=None):
        """Assign a lawyer to a case"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can assign lawyers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        case = self.get_object()
        serializer = CaseAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(case=case)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def upcoming_hearings(self, request):
        """Get upcoming hearings for the user"""
        base_queryset = self.get_queryset()
        if request.user.role == 'lawyer':
            base_queryset = base_queryset.filter(
                Q(assigned_lawyer=request.user) | Q(assignments__lawyer=request.user, assignments__is_active=True)
            ).distinct()
        cases = base_queryset.filter(
            next_hearing_date__gte=timezone.now().date(),
            status__in=['pending', 'active']
        ).order_by('next_hearing_date')[:10]
        serializer = CaseListSerializer(cases, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can finish cases'}, status=status.HTTP_403_FORBIDDEN)
        case = self.get_object()
        case.status = 'closed'
        case.save(update_fields=['status', 'updated_at'])
        return Response({'message': 'Case marked as finished', 'status': case.status})

    @action(detail=True, methods=['post'])
    def update_hearing(self, request, pk=None):
        """Admin or assigned judge: move next hearing forward and optionally attach documents."""
        case = self.get_object()
        if not self._can_write_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can update hearing date'}, status=status.HTTP_403_FORBIDDEN)

        new_date_raw = request.data.get('next_hearing_date')
        if not new_date_raw:
            return Response({'next_hearing_date': 'This field is required'}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import date
        try:
            new_date = date.fromisoformat(str(new_date_raw))
        except ValueError:
            return Response({'next_hearing_date': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.now().date()
        if new_date <= today:
            return Response({'next_hearing_date': 'Next hearing must be after today'}, status=status.HTTP_400_BAD_REQUEST)

        current = case.next_hearing_date
        if current and new_date <= current:
            return Response({'next_hearing_date': 'Next hearing must be later than current hearing date'}, status=status.HTTP_400_BAD_REQUEST)

        case.next_hearing_date = new_date
        case.save(update_fields=['next_hearing_date', 'updated_at'])
        hearing_event = self._create_hearing_event(case, new_date)
        uploaded_docs = self._save_request_documents(case, f"Uploaded with hearing update {new_date.isoformat()}")
        return Response({
            'message': 'Next hearing date updated',
            'next_hearing_date': new_date.isoformat(),
            'timeline_event': str(hearing_event.id),
            'documents_uploaded': len(uploaded_docs),
        })

    def _can_write_case(self, user, case):
        if user.role == 'admin':
            return True
        if user.role == 'judge':
            return case.assigned_judge_id == user.id or case.created_by_id == user.id
        return False

    def _save_request_documents(self, case, default_description=''):
        from apps.documents.models import CaseDocument
        from apps.ai_assistant.services import DocumentProcessor
        from apps.documents.models import DocumentExtraction
        files = self.request.FILES.getlist('files') or self.request.FILES.getlist('file')
        doc_types = self.request.data.getlist('document_types') if hasattr(self.request.data, 'getlist') else []
        descriptions = self.request.data.getlist('descriptions') if hasattr(self.request.data, 'getlist') else []
        uploaded = []
        for index, file_obj in enumerate(files):
            document_type = doc_types[index] if index < len(doc_types) and doc_types[index] else self.request.data.get('document_type', 'other')
            description = descriptions[index] if index < len(descriptions) and descriptions[index] else default_description
            doc = CaseDocument.objects.create(
                case=case,
                document_type=document_type,
                file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size,
                uploaded_by=self.request.user,
                description=description,
            )
            text = DocumentProcessor.extract_text(doc.file.path)
            DocumentExtraction.objects.update_or_create(
                document=doc,
                defaults={'extracted_text': text, 'ocr_text': '', 'metadata': {'source': 'upload'}},
            )
            uploaded.append(doc)
        return uploaded

    def _create_hearing_event(self, case, hearing_date):
        return CaseTimeline.objects.create(
            case=case,
            event_type='hearing',
            event_description=f"Hearing scheduled for {hearing_date.isoformat()}",
            event_date=hearing_date,
            notes='[AUTO_HEARING]',
            created_by=self.request.user
        )

    def _adjust_latest_hearing_event(self, case, old_date, new_date):
        if not new_date:
            return
        latest = CaseTimeline.objects.filter(
            case=case,
            event_type='hearing',
            notes__icontains='[AUTO_HEARING]'
        ).order_by('-created_at').first()
        if latest and (old_date is None or latest.event_date == old_date):
            latest.event_date = new_date
            latest.event_description = f"Hearing scheduled for {new_date.isoformat()}"
            latest.save(update_fields=['event_date', 'event_description', 'updated_at'])
        else:
            self._create_hearing_event(case, new_date)

    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        if request.user.role != 'lawyer':
            return Response({'error': 'Only lawyers can bookmark cases'}, status=status.HTTP_403_FORBIDDEN)
        case = self.get_object()
        assignment, _ = CaseAssignment.objects.get_or_create(
            case=case,
            lawyer=request.user,
            defaults={'role': 'assistant', 'is_active': True}
        )
        if not assignment.is_active:
            assignment.is_active = True
            assignment.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Case bookmarked'})

    @action(detail=True, methods=['post'])
    def unbookmark(self, request, pk=None):
        if request.user.role != 'lawyer':
            return Response({'error': 'Only lawyers can unbookmark cases'}, status=status.HTTP_403_FORBIDDEN)
        case = self.get_object()
        CaseAssignment.objects.filter(case=case, lawyer=request.user).update(is_active=False)
        return Response({'message': 'Case removed from bookmarks'})

    @action(detail=False, methods=['get'])
    def bookmarked(self, request):
        if request.user.role != 'lawyer':
            return Response({'error': 'Only lawyers can view bookmarks'}, status=status.HTTP_403_FORBIDDEN)
        cases = Case.objects.filter(
            Q(assigned_lawyer=request.user) | Q(assignments__lawyer=request.user, assignments__is_active=True)
        ).distinct().order_by('-created_at')
        serializer = CaseListSerializer(cases, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get case statistics"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only admins can view statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = {
            'total_cases': Case.objects.count(),
            'active_cases': Case.objects.filter(status='active').count(),
            'closed_cases': Case.objects.filter(status='closed').count(),
            'pending_cases': Case.objects.filter(status='pending').count(),
            'upcoming_hearings': Case.objects.filter(
                next_hearing_date__gte=timezone.now().date()
            ).count(),
        }
        return Response(stats)


class CaseTimelineViewSet(viewsets.ModelViewSet):
    """ViewSet for managing case timeline events"""
    
    queryset = CaseTimeline.objects.all()
    serializer_class = CaseTimelineSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['case', 'event_type']
    ordering = ['-event_date']


class CaseNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing case notes"""
    
    queryset = CaseNote.objects.all()
    serializer_class = CaseNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case', 'is_public']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return CaseNote.objects.all()
        # Lawyers see only public notes and their own notes
        return CaseNote.objects.filter(Q(is_public=True) | Q(author=user))
