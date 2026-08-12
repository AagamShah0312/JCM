"""
Views for tasks app.
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Task
from .serializers import TaskSerializer, TaskCreateSerializer
from apps.cases.permissions import can_view_task, task_queryset_for, can_view_case
from apps.common.exceptions import PermissionDeniedError, ValidationError_
from apps.cases.models import CaseEvent


class TaskViewSet(viewsets.ModelViewSet):
    """Task management for judges/lawyers."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'priority', 'assigned_to', 'case', 'due_date']
    ordering_fields = ['due_date', 'priority', 'created_at']
    ordering = ['-priority', 'due_date']

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskCreateSerializer
        return TaskSerializer

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def get_object(self):
        task = super().get_object()
        if not can_view_task(self.request.user, task):
            from apps.common.exceptions import NotFoundError
            raise NotFoundError('NOT_FOUND', 'Task not found')
        return task

    def perform_create(self, serializer):
        case = serializer.validated_data.get('case')
        assigned_to = serializer.validated_data.get('assigned_to')
        if case and not can_view_case(self.request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'You do not have access to this case')
        task = serializer.save(created_by=self.request.user)
        if case:
            CaseEvent.objects.create(
                case=case,
                event_type='TASK_CREATED',
                title=f"Task created: {task.title}",
                event_date=timezone.now().date(),
                created_by=self.request.user,
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        if task.assigned_to_id != request.user.id and request.user.role != 'admin':
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only the assignee or admin can complete this task')
        task.status = 'DONE'
        task.completed_at = timezone.now()
        task.save()
        if task.case:
            CaseEvent.objects.create(
                case=task.case,
                event_type='TASK_COMPLETED',
                title=f"Task completed: {task.title}",
                event_date=timezone.now().date(),
                created_by=request.user,
            )
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        task = self.get_object()
        status_val = request.data.get('status')
        valid = [s[0] for s in Task.STATUS_CHOICES]
        if status_val not in valid:
            raise ValidationError_('VALIDATION_ERROR', f'status must be one of {valid}')
        task.status = status_val
        if status_val == 'DONE':
            task.completed_at = timezone.now()
        task.save()
        return Response(TaskSerializer(task).data)
