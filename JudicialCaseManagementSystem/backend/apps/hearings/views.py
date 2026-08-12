"""
Views for hearings app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Hearing, HearingParticipant, HearingProceeding, AdjournmentReasonOption
from .serializers import (
    HearingSerializer, HearingCreateSerializer, HearingParticipantSerializer,
    HearingProceedingSerializer, HearingRescheduleSerializer, HearingCompleteSerializer,
    AdjournmentReasonOptionSerializer,
)
from apps.cases.permissions import (
    can_view_case, can_edit_case, can_view_hearing, can_edit_hearing,
    can_view_proceeding,
)
from apps.cases.models import Case, CaseEvent
from apps.audit.services import record_audit
from apps.common.exceptions import NotFoundError, PermissionDeniedError, ValidationError_
import logging

logger = logging.getLogger(__name__)


class HearingViewSet(viewsets.ModelViewSet):
    """First-class hearing management."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['case', 'status', 'date', 'judge', 'courtroom']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['date']

    def get_serializer_class(self):
        if self.action == 'create':
            return HearingCreateSerializer
        return HearingSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Hearing.objects.filter(is_public=True)
        if user.role == 'admin':
            return Hearing.objects.all()
        if user.role == 'guest':
            return Hearing.objects.filter(is_public=True)
        # judge/lawyer: hearings of cases they can view
        from apps.cases.permissions import case_queryset_for
        case_ids = case_queryset_for(user).values_list('id', flat=True)
        return Hearing.objects.filter(case_id__in=case_ids).distinct()

    def get_object(self):
        hearing = super().get_object()
        if not can_view_hearing(self.request.user, hearing):
            raise NotFoundError('NOT_FOUND', 'Hearing not found')
        return hearing

    def perform_create(self, serializer):
        case = serializer.validated_data.get('case')
        if not case:
            raise ValidationError_('VALIDATION_ERROR', 'case is required')
        if not can_edit_case(self.request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can create hearings')
        hearing = serializer.save(created_by=self.request.user)
        # Notify case participants
        try:
            from apps.notifications.services import notify_case_participants
            notify_case_participants(
                case, 'HEARING_CREATED',
                'Hearing Scheduled',
                f"Hearing #{hearing.hearing_number} scheduled for {hearing.date}",
                exclude_user=self.request.user,
            )
        except Exception:
            pass
        # Timeline event
        CaseEvent.objects.create(
            case=case,
            event_type='HEARING_CREATED',
            title=f"Hearing #{hearing.hearing_number} scheduled for {hearing.date}",
            description=hearing.purpose or '',
            event_date=hearing.date,
            related_entity=f"Hearing #{hearing.hearing_number}",
            created_by=self.request.user,
        )
        # Audit
        record_audit(
            user=self.request.user, action='HEARING_CREATED', model_name='Hearing',
            object_id=hearing.id, changes={'date': str(hearing.date)},
            ip_address='0.0.0.0', request_id=getattr(self.request, 'request_id', ''),
        )

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule a hearing (audit event required — spec §14/§15)."""
        hearing = self.get_object()
        if not can_edit_hearing(request.user, hearing):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can reschedule hearings')

        serializer = HearingRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        old_date = hearing.date
        hearing.date = data['new_date']
        if data.get('new_start_time'):
            hearing.start_time = data['new_start_time']
        if data.get('adjournment_reason'):
            code = data['adjournment_reason']
            reason = AdjournmentReasonOption.objects.filter(code=code).first()
            hearing.adjournment_reason = reason
            hearing.status = 'ADJOURNED'
        if data.get('adjournment_note'):
            hearing.adjournment_note = data['adjournment_note']
        hearing.save()

        try:
            from apps.notifications.services import notify_case_participants
            notify_case_participants(
                hearing.case, 'HEARING_RESCHEDULED',
                'Hearing Rescheduled',
                f"Hearing #{hearing.hearing_number} moved to {hearing.date}",
                exclude_user=request.user,
            )
        except Exception:
            pass
        # Timeline event + audit (never silently overwrite history)
        CaseEvent.objects.create(
            case=hearing.case,
            event_type='HEARING_RESCHEDULED',
            title=f"Hearing #{hearing.hearing_number} rescheduled from {old_date} to {hearing.date}",
            description=data.get('reason') or data.get('adjournment_note') or '',
            event_date=hearing.date,
            related_entity=f"Hearing #{hearing.hearing_number}",
            created_by=request.user,
        )
        record_audit(
            user=request.user, action='HEARING_RESCHEDULED', model_name='Hearing',
            object_id=hearing.id,
            changes={'old_date': str(old_date), 'new_date': str(hearing.date), 'reason': data.get('reason', '')},
            ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
            request_id=getattr(request, 'request_id', ''),
        )
        return Response(HearingSerializer(hearing, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark hearing completed + record proceedings (spec §15/§16)."""
        hearing = self.get_object()
        if not can_edit_hearing(request.user, hearing):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can record proceedings')

        serializer = HearingCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        hearing.status = 'COMPLETED'
        if data.get('adjournment_reason'):
            reason = AdjournmentReasonOption.objects.filter(code=data['adjournment_reason']).first()
            hearing.adjournment_reason = reason
            hearing.status = 'ADJOURNED'
        if data.get('adjournment_note'):
            hearing.adjournment_note = data['adjournment_note']
        if data.get('next_hearing_date'):
            hearing.next_hearing_date = data['next_hearing_date']
        hearing.save()

        proceeding = HearingProceeding.objects.create(
            hearing=hearing,
            summary=data.get('summary', ''),
            notes=data.get('notes', ''),
            submissions=data.get('submissions', ''),
            directions=data.get('directions', ''),
            attendance=data.get('attendance', ''),
            next_action=data.get('next_action', ''),
            next_hearing_date=data.get('next_hearing_date'),
            recorded_by=request.user,
        )
        doc_ids = data.get('documents', [])
        if doc_ids:
            from apps.documents.models import CaseDocument
            docs = CaseDocument.objects.filter(id__in=doc_ids, case=hearing.case)
            proceeding.documents_referenced.set(docs)

        CaseEvent.objects.create(
            case=hearing.case,
            event_type='HEARING_COMPLETED' if hearing.status == 'COMPLETED' else 'HEARING_ADJOURNED',
            title=f"Hearing #{hearing.hearing_number} {'completed' if hearing.status == 'COMPLETED' else 'adjourned'}",
            description=data.get('summary', '')[:500],
            event_date=timezone.now().date(),
            related_entity=f"Hearing #{hearing.hearing_number}",
            created_by=request.user,
        )
        record_audit(
            user=request.user, action='PROCEEDINGS_CREATED', model_name='HearingProceeding',
            object_id=proceeding.id, changes={'hearing_status': hearing.status},
            ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
            request_id=getattr(request, 'request_id', ''),
        )
        return Response(HearingSerializer(hearing, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        hearing = self.get_object()
        if not can_edit_hearing(request.user, hearing):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can cancel hearings')
        reason = request.data.get('reason', '')
        hearing.status = 'CANCELLED'
        hearing.adjournment_note = reason
        hearing.save()
        CaseEvent.objects.create(
            case=hearing.case,
            event_type='HEARING_CANCELLED',
            title=f"Hearing #{hearing.hearing_number} cancelled",
            description=reason,
            event_date=timezone.now().date(),
            created_by=request.user,
        )
        record_audit(user=request.user, action='HEARING_CANCELLED', model_name='Hearing',
                     object_id=hearing.id, changes={'reason': reason},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response(HearingSerializer(hearing, context={'request': request}).data)

    @action(detail=True, methods=['get', 'post'])
    def participants(self, request, pk=None):
        hearing = self.get_object()
        if request.method == 'POST':
            if not can_edit_hearing(request.user, hearing):
                raise PermissionDeniedError('PERMISSION_DENIED')
            serializer = HearingParticipantSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(hearing=hearing)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        serializer = HearingParticipantSerializer(hearing.participants.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def proceedings(self, request, pk=None):
        hearing = self.get_object()
        if request.method == 'POST':
            if not can_edit_hearing(request.user, hearing):
                raise PermissionDeniedError('PERMISSION_DENIED')
            serializer = HearingProceedingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(hearing=hearing, recorded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        procs = [p for p in hearing.proceedings.all() if can_view_proceeding(request.user, p)]
        serializer = HearingProceedingSerializer(procs, many=True)
        return Response(serializer.data)


class AdjournmentReasonViewSet(viewsets.ReadOnlyModelViewSet):
    """Configurable adjournment reasons (spec §41)."""
    permission_classes = [IsAuthenticated]
    serializer_class = AdjournmentReasonOptionSerializer
    queryset = AdjournmentReasonOption.objects.filter(is_active=True).order_by('code')
