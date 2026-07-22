"""
Django models for cases app
"""
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
import uuid
import uuid as uuid_module


class Case(models.Model):
    """Core Case model"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('appealed', 'Appealed'),
        ('closed', 'Closed'),
        ('postponed', 'Postponed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_number = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    court_name = models.CharField(max_length=255)
    case_type = models.CharField(max_length=100)  # Criminal, Civil, Corporate, etc.
    filing_date = models.DateField()
    next_hearing_date = models.DateField(null=True, blank=True)
    public_interest_link = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    judge_name = models.CharField(max_length=255, blank=True)
    assigned_judge = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='judged_cases',
        limit_choices_to={'role': 'judge'}
    )
    plaintiff_name = models.CharField(max_length=255)
    defendant_name = models.CharField(max_length=255)
    assigned_lawyer = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cases'
    )
    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.PROTECT,
        related_name='created_cases'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case_number']),
            models.Index(fields=['status']),
            models.Index(fields=['assigned_lawyer']),
            models.Index(fields=['assigned_judge']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('can_view_all_cases', 'Can view all cases'),
            ('can_edit_case', 'Can edit case details'),
        ]
    
    def __str__(self):
        return f"{self.case_number} - {self.title}"


class CaseTimeline(models.Model):
    """Track case events and milestones"""
    
    EVENT_TYPES = (
        ('filing', 'Filing'),
        ('hearing', 'Hearing'),
        ('judgment', 'Judgment'),
        ('appeal', 'Appeal'),
        ('hearing_rescheduled', 'Hearing Rescheduled'),
        ('postponed', 'Postponed'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_description = models.TextField()
    event_date = models.DateField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-event_date']
        indexes = [
            models.Index(fields=['case', 'event_date']),
        ]
    
    def __str__(self):
        return f"{self.case.case_number} - {self.event_type} on {self.event_date}"


class CaseAssignment(models.Model):
    """Track lawyer assignments to cases"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='assignments')
    lawyer = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='case_assignments'
    )
    assigned_date = models.DateField(auto_now_add=True)
    role = models.CharField(
        max_length=50,
        choices=[('primary', 'Primary'), ('co_counsel', 'Co-Counsel'), ('assistant', 'Assistant')]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['case', 'lawyer']
        indexes = [
            models.Index(fields=['lawyer', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.lawyer.email} - {self.case.case_number}"


class CaseNote(models.Model):
    """Internal notes on cases"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    is_public = models.BooleanField(default=False)  # Visible to assigned lawyers
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note on {self.case.case_number} by {self.author.email}"
