"""
Hearings app models: Hearing, HearingParticipant, HearingProceeding.
"""
import uuid

from django.db import models


class AdjournmentReasonOption(models.Model):
    """Configurable adjournment reasons for analytics."""
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} ({self.label})"


class Hearing(models.Model):
    """A first-class hearing for a case."""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ADJOURNED', 'Adjourned'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='hearings')
    hearing_number = models.PositiveIntegerField(default=0, help_text='Sequential hearing number within the case')
    date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    courtroom = models.ForeignKey(
        'courts.Courtroom', on_delete=models.SET_NULL, null=True, blank=True, related_name='hearings'
    )
    judge = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='presided_hearings', limit_choices_to={'role': 'judge'}
    )
    hearing_type = models.CharField(
        max_length=50,
        choices=[
            ('FIRST', 'First Hearing'),
            ('ARGUMENTS', 'Arguments'),
            ('EVIDENCE', 'Evidence Recording'),
            ('ORDER', 'Order/Judgment'),
            ('INTERIM', 'Interim Application'),
            ('ADJOURNMENT', 'Adjournment'),
            ('OTHER', 'Other'),
        ],
        default='FIRST',
    )
    purpose = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED', db_index=True)
    adjournment_reason = models.ForeignKey(
        AdjournmentReasonOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hearings'
    )
    adjournment_note = models.TextField(blank=True)
    next_hearing_date = models.DateField(null=True, blank=True)
    next_hearing_notes = models.TextField(blank=True)
    is_public = models.BooleanField(default=False, help_text='Public hearing date/time visible to guests')
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, related_name='created_hearings'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['case', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['judge', 'date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Hearing #{self.hearing_number} - {self.case.case_number} on {self.date}"

    def save(self, *args, **kwargs):
        if not self.hearing_number:
            last = Hearing.objects.filter(case=self.case).order_by('-hearing_number').first()
            self.hearing_number = (last.hearing_number + 1) if last else 1
        super().save(*args, **kwargs)


class HearingParticipant(models.Model):
    """Attendance/participant record for a hearing."""
    ROLE_CHOICES = [
        ('judge', 'Judge'),
        ('lawyer', 'Lawyer'),
        ('petitioner', 'Petitioner'),
        ('respondent', 'Respondent'),
        ('witness', 'Witness'),
        ('court_staff', 'Court Staff'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('REPRESENTED', 'Represented'),
        ('EXCUSED', 'Excused'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hearing = models.ForeignKey(Hearing, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hearing_attendances'
    )
    name = models.CharField(max_length=255, blank=True, help_text='Free-text name when no user account')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role', 'name']
        indexes = [models.Index(fields=['hearing', 'role'])]

    def __str__(self):
        return f"{self.name or self.user} ({self.get_role_display()}) - {self.hearing}"


class HearingProceeding(models.Model):
    """Recorded proceedings of a completed hearing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hearing = models.ForeignKey(Hearing, on_delete=models.CASCADE, related_name='proceedings')
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    submissions = models.TextField(blank=True)
    directions = models.TextField(blank=True)
    attendance = models.TextField(blank=True)
    documents_referenced = models.ManyToManyField(
        'documents.CaseDocument', blank=True, related_name='referenced_in_proceedings'
    )
    next_action = models.TextField(blank=True)
    next_hearing_date = models.DateField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, related_name='recorded_proceedings'
    )
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['hearing'])]

    def __str__(self):
        return f"Proceeding for {self.hearing}"
