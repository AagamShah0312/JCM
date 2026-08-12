"""
Tasks app models: Task (judge/lawyer work items).
"""
import uuid

from django.db import models


class Task(models.Model):
    """A work item assigned to a user, optionally tied to a case/hearing/document."""
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('BLOCKED', 'Blocked'),
        ('DONE', 'Done'),
        ('CANCELLED', 'Cancelled'),
    ]
    PRIORITY_CHOICES = [
        ('URGENT', 'Urgent'),
        ('HIGH', 'High'),
        ('NORMAL', 'Normal'),
        ('LOW', 'Low'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    case = models.ForeignKey(
        'cases.Case', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks'
    )
    hearing = models.ForeignKey(
        'hearings.Hearing', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    document = models.ForeignKey(
        'documents.CaseDocument', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks'
    )
    assigned_to = models.ForeignKey(
        'authentication.User', on_delete=models.CASCADE, related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, related_name='created_tasks'
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='NORMAL', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO', db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'due_date', 'created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['assigned_to', 'due_date']),
            models.Index(fields=['case']),
        ]

    def __str__(self):
        return f"{self.title} -> {self.assigned_to.email}"
