"""
Views for cases app (enterprise version).
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
from .models import (
    Case, CaseEvent, CaseAssignment, CaseNote, CaseParty, CaseLawyer,
    CaseStatusHistory,
)
from .serializers import (
    CaseDetailSerializer, CaseListSerializer, CaseEventSerializer,
    CaseAssignmentSerializer, CaseNoteSerializer, CaseUpdateSerializer,
    CaseCreateSerializer, CasePartySerializer, CaseLawyerSerializer,
    CaseStatusHistorySerializer, GuestCaseSerializer, LawyerCaseSerializer,
    JudgeCaseSerializer, AdminCaseSerializer,
)
from .permissions import (
    can_view_case, can_edit_case, can_delete_case, case_queryset_for,
)
import logging

logger = logging.getLogger(__name__)


class CaseViewSet(viewsets.ModelViewSet):
    """ViewSet for case management"""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'case_type', 'priority', 'court', 'filing_date']
    search_fields = ['case_number', 'cnr_number', 'title', 'plaintiff_name', 'defendant_name', 'judge_name']
    ordering_fields = ['created_at', 'filing_date', 'next_hearing_date', 'status', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        return case_queryset_for(self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CaseDetailSerializer
        elif self.action == 'create':
            return CaseCreateSerializer
        elif self.action in ('update', 'partial_update'):
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
        # Record case-filed event
        CaseEvent.objects.create(
            case=case,
            event_type='CASE_FILED',
            title=f"Case filed as {case.case_number}",
            description=case.description[:500],
            event_date=case.filing_date or timezone.now().date(),
            created_by=self.request.user,
        )
        if case.next_hearing_date:
            self._create_hearing_event(case, case.next_hearing_date)

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['admin', 'judge']:
            return Response({'error': 'Only admins and judges can create cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        case = self.get_object()
        if not can_edit_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can update cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        case = self.get_object()
        if not can_edit_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can update cases'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not can_delete_case(request.user, self.get_object()):
            return Response({'error': 'Only admins can delete cases'}, status=status.HTTP_403_FORBIDDEN)
        # Soft-delete: archive instead of hard delete for judicial records
        case = self.get_object()
        case.is_archived = True
        case.deleted_at = timezone.now()
        case.deleted_by = request.user
        case.save(update_fields=['is_archived', 'deleted_at', 'deleted_by', 'updated_at'])
        return Response({'message': 'Case archived'}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        """Log case updates + status transitions"""
        old_status = serializer.instance.status
        old_next_hearing_date = serializer.instance.next_hearing_date
        instance = serializer.save()
        if old_status != instance.status:
            CaseStatusHistory.objects.create(
                case=instance, from_status=old_status, to_status=instance.status,
                changed_by=self.request.user,
            )
            CaseEvent.objects.create(
                case=instance,
                event_type='STATUS_CHANGED',
                title=f"Status changed: {old_status} → {instance.status}",
                event_date=timezone.now().date(),
                created_by=self.request.user,
            )
        if old_next_hearing_date != instance.next_hearing_date:
            self._adjust_latest_hearing_event(instance, old_next_hearing_date, instance.next_hearing_date)
        logger.info(f"Case {instance.case_number} updated by {self.request.user.email}")

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get case timeline (unified events)"""
        case = self.get_object()
        events = case.events.all()
        serializer = CaseEventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_timeline_event(self, request, pk=None):
        """Add a timeline event to a case"""
        case = self.get_object()
        if not can_edit_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can add timeline events'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = CaseEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(case=case, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def notes(self, request, pk=None):
        """Get or add notes to a case"""
        case = self.get_object()

        if request.method == 'POST':
            if not can_view_case(request.user, case):
                raise PermissionDenied("You are not authorized to this case")
            serializer = CaseNoteSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(case=case, author=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        notes = case.notes.all()
        serializer = CaseNoteSerializer(notes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def parties(self, request, pk=None):
        """Get or add parties to a case"""
        case = self.get_object()
        if request.method == 'POST':
            if not can_edit_case(request.user, case):
                return Response({'error': 'Only admins or the assigned judge can add parties'},
                                status=status.HTTP_403_FORBIDDEN)
            serializer = CasePartySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(case=case)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = CasePartySerializer(case.parties.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def case_lawyers(self, request, pk=None):
        """Get or add lawyers to a case"""
        case = self.get_object()
        if request.method == 'POST':
            if not can_edit_case(request.user, case):
                return Response({'error': 'Only admins or the assigned judge can add lawyers'},
                                status=status.HTTP_403_FORBIDDEN)
            serializer = CaseLawyerSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(case=case)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = CaseLawyerSerializer(case.case_lawyers.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def status_history(self, request, pk=None):
        """Get case status transition history"""
        case = self.get_object()
        serializer = CaseStatusHistorySerializer(case.status_history.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change case status with validation + audit"""
        case = self.get_object()
        if not can_edit_case(request.user, case):
            return Response({'error': 'Only admins or the assigned judge can change status'},
                            status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        if not new_status:
            return Response({'status': 'This field is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            changed = case.change_status(new_status, actor=request.user, reason=reason)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not changed:
            return Response({'message': 'Status unchanged', 'status': case.status})
        CaseEvent.objects.create(
            case=case,
            event_type='STATUS_CHANGED',
            title=f"Status changed to {case.get_status_display()}",
            description=reason,
            event_date=timezone.now().date(),
            created_by=request.user,
        )
        return Response({'message': 'Status updated', 'status': case.status})

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
            lawyer = serializer.validated_data['lawyer']
            assignment_fields = {
                key: value for key, value in serializer.validated_data.items()
                if key not in ('case', 'lawyer')
            }
            assignment, created = CaseAssignment.objects.get_or_create(
                case=case,
                lawyer=lawyer,
                defaults=assignment_fields,
            )
            if not created:
                for key, value in assignment_fields.items():
                    setattr(assignment, key, value)
                assignment.is_active = True
                assignment.save(update_fields=list(assignment_fields.keys()) + ['is_active', 'updated_at'])
            CaseEvent.objects.create(
                case=case,
                event_type='LAWYER_ASSIGNED',
                title=f"Lawyer {lawyer.get_full_name() or lawyer.email} assigned",
                event_date=timezone.now().date(),
                created_by=request.user,
            )
            output = CaseAssignmentSerializer(assignment).data
            return Response(output, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
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
            status__in=['PENDING', 'ACTIVE', 'ADJOURNED', 'FILED', 'REGISTERED']
        ).order_by('next_hearing_date')[:10]
        serializer = CaseListSerializer(cases, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can finish cases'}, status=status.HTTP_403_FORBIDDEN)
        case = self.get_object()
        try:
            case.change_status('CLOSED', actor=request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Case marked as finished', 'status': case.status})

    @action(detail=True, methods=['post'])
    def update_hearing(self, request, pk=None):
        """Admin or assigned judge: move next hearing forward and optionally attach documents."""
        case = self.get_object()
        if not can_edit_case(request.user, case):
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
        return can_edit_case(user, case)

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
        return CaseEvent.objects.create(
            case=case,
            event_type='HEARING_CREATED',
            title=f"Hearing scheduled for {hearing_date.isoformat()}",
            description=f"Hearing scheduled for {hearing_date.isoformat()}",
            event_date=hearing_date,
            created_by=self.request.user,
        )

    def _adjust_latest_hearing_event(self, case, old_date, new_date):
        if not new_date:
            return
        latest = CaseEvent.objects.filter(
            case=case,
            event_type='HEARING_CREATED',
        ).order_by('-created_at').first()
        if latest and (old_date is None or latest.event_date == old_date):
            latest.event_date = new_date
            latest.title = f"Hearing scheduled for {new_date.isoformat()}"
            latest.save(update_fields=['event_date', 'title', 'created_at'])
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
            'active_cases': Case.objects.filter(status='ACTIVE').count(),
            'closed_cases': Case.objects.filter(status='CLOSED').count(),
            'pending_cases': Case.objects.filter(status__in=['PENDING', 'FILED', 'REGISTERED']).count(),
            'upcoming_hearings': Case.objects.filter(
                next_hearing_date__gte=timezone.now().date()
            ).count(),
        }
        return Response(stats)


class CaseEventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing case timeline events"""

    queryset = CaseEvent.objects.all()
    serializer_class = CaseEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['case', 'event_type']
    ordering = ['-event_date']

    def get_queryset(self):
        return CaseEvent.objects.filter(case__in=case_queryset_for(self.request.user))


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
