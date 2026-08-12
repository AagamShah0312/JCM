"""
Courts app models: Court and Courtroom.
"""
import uuid

from django.db import models


class Court(models.Model):
    """A court that hears cases."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    court_type = models.CharField(
        max_length=50,
        choices=[
            ('supreme', 'Supreme Court'),
            ('high', 'High Court'),
            ('district', 'District Court'),
            ('session', 'Sessions Court'),
            ('civil', 'Civil Court'),
            ('criminal', 'Criminal Court'),
            ('family', 'Family Court'),
            ('tribunal', 'Tribunal'),
            ('other', 'Other'),
        ],
        default='other',
    )
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['court_type']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return self.name


class Courtroom(models.Model):
    """A courtroom (physical/functional room) inside a court."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='courtrooms')
    name = models.CharField(max_length=100)
    floor = models.CharField(max_length=50, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['court', 'name']
        unique_together = ['court', 'name']

    def __str__(self):
        return f"{self.court.name} / {self.name}"
