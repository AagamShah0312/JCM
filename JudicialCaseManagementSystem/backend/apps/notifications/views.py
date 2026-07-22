"""
Views for notifications app
"""
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Notification, NotificationSchedule
from .serializers import NotificationSerializer, NotificationScheduleSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications"""
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'is_read']
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        unread = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(unread, many=True)
        return Response({
            'count': unread.count(),
            'notifications': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})
    
    @action(detail=False, methods=['delete'])
    def clear_old(self, request):
        """Clear notifications older than 30 days"""
        from django.utils import timezone
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        deleted_count, _ = Notification.objects.filter(
            user=request.user,
            created_at__lt=thirty_days_ago
        ).delete()
        return Response({'deleted': deleted_count})


class NotificationScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for scheduled notifications"""
    
    serializer_class = NotificationScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['case', 'is_sent']
    
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return NotificationSchedule.objects.all()
        return NotificationSchedule.objects.filter(recipients=self.request.user)
