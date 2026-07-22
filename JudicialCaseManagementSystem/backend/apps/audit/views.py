"""
Views for audit app
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audit logs (read-only)"""
    
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'action', 'model_name']
    
    def get_queryset(self):
        # Only admins can view all logs, users see only their own
        if self.request.user.role == 'admin':
            return AuditLog.objects.all().order_by('-created_at')
        return AuditLog.objects.filter(user=self.request.user).order_by('-created_at')
