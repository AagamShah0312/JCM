"""
Django models for audit app
"""
from django.db import models
import uuid


class AuditLog(models.Model):
    """Log all important actions for audit trail"""
    
    ACTIONS = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('download', 'Download'),
        ('upload', 'Upload'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTIONS)
    model_name = models.CharField(max_length=100)  # Case, Document, etc.
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)  # What changed
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]
    
    def __str__(self):
        user_label = self.user.email if self.user else "deleted-user"
        return f"{user_label} - {self.action} on {self.model_name}"
