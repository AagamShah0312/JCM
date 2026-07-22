"""
Django models for notifications app
"""
from django.db import models
import uuid


class Notification(models.Model):
    """User notifications"""
    
    TYPES = (
        ('case_assigned', 'Case Assigned'),
        ('hearing_scheduled', 'Hearing Scheduled'),
        ('document_uploaded', 'Document Uploaded'),
        ('case_updated', 'Case Updated'),
        ('message', 'Message'),
        ('system', 'System'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"


class NotificationSchedule(models.Model):
    """Schedule notifications for future dates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='notification_schedules'
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    notification_type = models.CharField(max_length=50, choices=Notification.TYPES)
    message = models.TextField()
    recipients = models.ManyToManyField('authentication.User', related_name='scheduled_notifications')
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"Notification scheduled for {self.scheduled_date}"
