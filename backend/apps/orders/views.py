"""
Views for orders app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone

from .models import Order, OrderVersion
from .serializers import OrderSerializer, OrderCreateSerializer, OrderVersionSerializer
from apps.cases.permissions import (
    can_view_case, can_edit_case, can_view_order, case_queryset_for,
)
from apps.cases.models import CaseEvent
from apps.audit.services import record_audit
from apps.common.exceptions import PermissionDeniedError, NotFoundError, ValidationError_
import logging

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    """Order management with draft/sign/publish/supersede lifecycle."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['case', 'status', 'order_type', 'date']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Order.objects.filter(is_public=True, status='PUBLISHED')
        if user.role == 'admin':
            return Order.objects.all()
        if user.role == 'guest':
            return Order.objects.filter(is_public=True, status='PUBLISHED')
        case_ids = case_queryset_for(user).values_list('id', flat=True)
        return Order.objects.filter(case_id__in=case_ids).distinct()

    def get_object(self):
        order = super().get_object()
        if not can_view_order(self.request.user, order):
            raise NotFoundError('NOT_FOUND', 'Order not found')
        return order

    def perform_create(self, serializer):
        case = serializer.validated_data.get('case')
        if not case:
            raise ValidationError_('VALIDATION_ERROR', 'case is required')
        if not can_edit_case(self.request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can create orders')
        order = serializer.save(created_by=self.request.user)
        # First version
        OrderVersion.objects.create(
            order=order,
            version_number=1,
            document=order.document,
            content_text=order.summary,
            reason='Initial version',
            uploaded_by=self.request.user,
        )
        CaseEvent.objects.create(
            case=case,
            event_type='ORDER_CREATED',
            title=f"Order created: {order.title}",
            description=order.summary[:500],
            event_date=order.date or timezone.now().date(),
            related_entity=f"Order {order.order_number or order.id}",
            created_by=self.request.user,
        )
        record_audit(user=self.request.user, action='ORDER_CREATED', model_name='Order',
                     object_id=order.id, changes={'title': order.title},
                     ip_address=self.request.META.get('REMOTE_ADDR', '0.0.0.0'))

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an order (becomes visible per its visibility/is_public)."""
        order = self.get_object()
        if not can_edit_case(request.user, order.case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can publish orders')
        order.status = 'PUBLISHED'
        order.published_at = timezone.now()
        order.save()
        try:
            from apps.notifications.services import notify_case_participants
            notify_case_participants(
                order.case, 'ORDER_PUBLISHED',
                'Order Published',
                f"Order published: {order.title}",
                exclude_user=request.user,
            )
        except Exception:
            pass
        CaseEvent.objects.create(
            case=order.case,
            event_type='ORDER_PUBLISHED',
            title=f"Order published: {order.title}",
            event_date=timezone.now().date(),
            related_entity=f"Order {order.order_number or order.id}",
            created_by=request.user,
        )
        record_audit(user=request.user, action='ORDER_PUBLISHED', model_name='Order',
                     object_id=order.id, changes={},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response(OrderSerializer(order, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        order = self.get_object()
        if not can_edit_case(request.user, order.case):
            raise PermissionDeniedError('PERMISSION_DENIED')
        order.status = 'SIGNED'
        order.save()
        return Response(OrderSerializer(order, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def supersede(self, request, pk=None):
        """Mark this order superseded by another (version history preserved)."""
        order = self.get_object()
        if not can_edit_case(request.user, order.case):
            raise PermissionDeniedError('PERMISSION_DENIED')
        new_order_id = request.data.get('superseded_by')
        if not new_order_id:
            raise ValidationError_('VALIDATION_ERROR', 'superseded_by is required')
        new_order = Order.objects.filter(id=new_order_id).first()
        if not new_order:
            raise NotFoundError('NOT_FOUND', 'New order not found')
        order.status = 'SUPERSEDED'
        order.superseded_by = new_order
        order.save()
        return Response(OrderSerializer(order, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def new_version(self, request, pk=None):
        """Create a new version of the order (append-only history)."""
        order = self.get_object()
        if not can_edit_case(request.user, order.case):
            raise PermissionDeniedError('PERMISSION_DENIED')
        last = order.versions.order_by('-version_number').first()
        version_number = (last.version_number + 1) if last else 1
        doc = request.data.get('document')
        content_text = request.data.get('content_text', '')
        reason = request.data.get('reason', '')
        version = OrderVersion.objects.create(
            order=order,
            version_number=version_number,
            document_id=doc or None,
            content_text=content_text,
            reason=reason,
            uploaded_by=request.user,
        )
        record_audit(user=request.user, action='ORDER_UPDATED', model_name='OrderVersion',
                     object_id=version.id, changes={'version_number': version_number, 'reason': reason},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response(OrderVersionSerializer(version).data, status=status.HTTP_201_CREATED)
