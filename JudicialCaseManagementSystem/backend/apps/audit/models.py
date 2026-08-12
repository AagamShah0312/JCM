"""
Audit app models: append-only audit logging for sensitive operations.
"""
import uuid

from django.db import models


class AuditEventType:
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    CASE_CREATED = 'CASE_CREATED'
    CASE_UPDATED = 'CASE_UPDATED'
    CASE_ASSIGNED = 'CASE_ASSIGNED'
    CASE_DELETED = 'CASE_DELETED'
    CASE_STATUS_CHANGED = 'CASE_STATUS_CHANGED'
    HEARING_CREATED = 'HEARING_CREATED'
    HEARING_UPDATED = 'HEARING_UPDATED'
    HEARING_RESCHEDULED = 'HEARING_RESCHEDULED'
    HEARING_CANCELLED = 'HEARING_CANCELLED'
    PROCEEDINGS_CREATED = 'PROCEEDINGS_CREATED'
    PROCEEDINGS_UPDATED = 'PROCEEDINGS_UPDATED'
    DOCUMENT_UPLOADED = 'DOCUMENT_UPLOADED'
    DOCUMENT_VIEWED = 'DOCUMENT_VIEWED'
    DOCUMENT_DOWNLOADED = 'DOCUMENT_DOWNLOADED'
    DOCUMENT_DELETED = 'DOCUMENT_DELETED'
    DOCUMENT_VERSION_CREATED = 'DOCUMENT_VERSION_CREATED'
    DOCUMENT_VISIBILITY_CHANGED = 'DOCUMENT_VISIBILITY_CHANGED'
    ORDER_CREATED = 'ORDER_CREATED'
    ORDER_UPDATED = 'ORDER_UPDATED'
    ORDER_PUBLISHED = 'ORDER_PUBLISHED'
    USER_CREATED = 'USER_CREATED'
    USER_UPDATED = 'USER_UPDATED'
    PERMISSION_CHANGED = 'PERMISSION_CHANGED'
    TASK_CREATED = 'TASK_CREATED'
    TASK_UPDATED = 'TASK_UPDATED'
    CSV_IMPORT = 'CSV_IMPORT'
    AI_QUERY = 'AI_QUERY'
    OTHER = 'OTHER'

    CHOICES = [
        (LOGIN, 'Login'),
        (LOGOUT, 'Logout'),
        (CASE_CREATED, 'Case Created'),
        (CASE_UPDATED, 'Case Updated'),
        (CASE_ASSIGNED, 'Case Assigned'),
        (CASE_DELETED, 'Case Deleted'),
        (CASE_STATUS_CHANGED, 'Case Status Changed'),
        (HEARING_CREATED, 'Hearing Created'),
        (HEARING_UPDATED, 'Hearing Updated'),
        (HEARING_RESCHEDULED, 'Hearing Rescheduled'),
        (HEARING_CANCELLED, 'Hearing Cancelled'),
        (PROCEEDINGS_CREATED, 'Proceedings Created'),
        (PROCEEDINGS_UPDATED, 'Proceedings Updated'),
        (DOCUMENT_UPLOADED, 'Document Uploaded'),
        (DOCUMENT_VIEWED, 'Document Viewed'),
        (DOCUMENT_DOWNLOADED, 'Document Downloaded'),
        (DOCUMENT_DELETED, 'Document Deleted'),
        (DOCUMENT_VERSION_CREATED, 'Document Version Created'),
        (DOCUMENT_VISIBILITY_CHANGED, 'Document Visibility Changed'),
        (ORDER_CREATED, 'Order Created'),
        (ORDER_UPDATED, 'Order Updated'),
        (ORDER_PUBLISHED, 'Order Published'),
        (USER_CREATED, 'User Created'),
        (USER_UPDATED, 'User Updated'),
        (PERMISSION_CHANGED, 'Permission Changed'),
        (TASK_CREATED, 'Task Created'),
        (TASK_UPDATED, 'Task Updated'),
        (CSV_IMPORT, 'CSV Import'),
        (AI_QUERY, 'AI Query'),
        (OTHER, 'Other'),
    ]


class AuditLog(models.Model):
    """Append-only log of all important actions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=AuditEventType.CHOICES, db_index=True)
    model_name = models.CharField(max_length=100)  # Case, Document, Hearing, ...
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict)
    status_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['model_name', 'object_id']),
        ]

    def delete(self, *args, **kwargs):
        # Append-only: audit logs cannot be deleted through the ORM.
        raise NotImplementedError("Audit logs are append-only and cannot be deleted")

    def save(self, *args, **kwargs):
        if not self.pk and 'update_fields' in kwargs:
            kwargs['update_fields'] = None
        super().save(*args, **kwargs)

    def __str__(self):
        user_label = self.user.email if self.user else "deleted-user"
        return f"{user_label} - {self.action} on {self.model_name}"


class AuditLogManager(models.Manager):
    """Queryset for reading audit logs (no create path)."""

    def create_audit(self, *, user, action, model_name, object_id, changes=None,
                     ip_address='0.0.0.0', user_agent='', request_id='', metadata=None,
                     status_code=None):
        """Create an audit record (append-only)."""
        log = AuditLog(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            metadata=metadata or {},
            status_code=status_code,
        )
        log.save()
        return log
