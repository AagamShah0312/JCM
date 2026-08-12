"""
Views for courts app.
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Court, Courtroom
from .serializers import CourtSerializer, CourtroomSerializer


class CourtViewSet(viewsets.ModelViewSet):
    """Court management (admin-only writes)."""
    serializer_class = CourtSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['court_type', 'state', 'is_active']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Court.objects.filter(is_active=True).prefetch_related('courtrooms')


class CourtroomViewSet(viewsets.ModelViewSet):
    """Courtroom management (admin-only writes)."""
    serializer_class = CourtroomSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['court', 'is_active']
    ordering = ['court', 'name']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Courtroom.objects.filter(is_active=True)
