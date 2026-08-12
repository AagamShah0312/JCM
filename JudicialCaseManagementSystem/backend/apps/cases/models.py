"""
Django models for cases app.

Enterprise data model for the JCM platform. The Case entity is the hub of the
system; parties, lawyers, hearings, proceedings, orders, documents, events,
tasks and AI conversations all hang off it.
"""
from django.db import models
import uuid


class CaseStatus:
    """Canonical case statuses (configurable via CaseStatusOption)."""
    FILED = 'FILED'
    REGISTERED = 'REGISTERED'
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'
    ADJOURNED = 'ADJOURNED'
    RESERVED_FOR_ORDER = 'RESERVED_FOR_ORDER'
    DISPOSED = 'DISPOSED'
    TRANSFERRED = 'TRANSFERRED'
    CLOSED = 'CLOSED'

    CHOICES = [
        (FILED, 'Filed'),
        (REGISTERED, 'Registered'),
        (PENDING, 'Pending'),
        (ACTIVE, 'Active'),
        (ADJOURNED, 'Adjourned'),
        (RESERVED_FOR_ORDER, 'Reserved for Order'),
        (DISPOSED, 'Disposed'),
        (TRANSFERRED, 'Transferred'),
        (CLOSED, 'Closed'),
    ]

    # Legal, auditable transitions. Only these are allowed.
    TRANSITIONS = {
        FILED: {REGISTERED, PENDING, ACTIVE, DISPOSED, TRANSFERRED, CLOSED},
        REGISTERED: {PENDING, ACTIVE, ADJOURNED, RESERVED_FOR_ORDER, DISPOSED, TRANSFERRED, CLOSED},
        PENDING: {ACTIVE, ADJOURNED, RESERVED_FOR_ORDER, DISPOSED, TRANSFERRED, CLOSED},
        ACTIVE: {PENDING, ADJOURNED, RESERVED_FOR_ORDER, DISPOSED, TRANSFERRED},
        ADJOURNED: {PENDING, ACTIVE, RESERVED_FOR_ORDER, DISPOSED, TRANSFERRED, CLOSED},
        RESERVED_FOR_ORDER: {ACTIVE, DISPOSED, CLOSED},
        DISPOSED: {CLOSED},
        TRANSFERRED: {CLOSED},
        CLOSED: set(),
    }

    @classmethod
    def is_valid_transition(cls, current, new):
        return new in cls.TRANSITIONS.get(current, set())


class CasePriority:
    URGENT = 'URGENT'
    HIGH = 'HIGH'
    NORMAL = 'NORMAL'
    LOW = 'LOW'

    CHOICES = [
        (URGENT, 'Urgent'),
        (HIGH, 'High'),
        (NORMAL, 'Normal'),
        (LOW, 'Low'),
    ]


class Case(models.Model):
    """Core Case entity."""

    # Backwards-compatible statuses map to the enterprise set.
    STATUS_CHOICES = CaseStatus.CHOICES
    PRIORITY_CHOICES = CasePriority.CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_number = models.CharField(max_length=50, unique=True, db_index=True)
    cnr_number = models.CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    court = models.ForeignKey(
        'courts.Court',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cases',
    )
    courtroom = models.ForeignKey(
        'courts.Courtroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cases',
    )
    court_name = models.CharField(max_length=255, blank=True)  # legacy free-text court
    case_type = models.CharField(max_length=100, db_index=True)  # Criminal, Civil, Corporate, ...
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=CasePriority.NORMAL, db_index=True)
    filing_date = models.DateField()
    registration_date = models.DateField(null=True, blank=True)
    next_hearing_date = models.DateField(null=True, blank=True, db_index=True)
    public_interest_link = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=CaseStatus.FILED, db_index=True)
    judge_name = models.CharField(max_length=255, blank=True)  # legacy free-text judge
    assigned_judge = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='judged_cases',
        limit_choices_to={'role': 'judge'}
    )
    plaintiff_name = models.CharField(max_length=255, blank=True)  # legacy single petitioner
    defendant_name = models.CharField(max_length=255, blank=True)  # legacy single respondent
    assigned_lawyer = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cases',
        limit_choices_to={'role': 'lawyer'}
    )
    # Disposal info
    disposal_date = models.DateField(null=True, blank=True)
    disposal_reason = models.CharField(max_length=255, blank=True)
    # Extensibility: configurable subject/category
    subject = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    # Flags
    is_public = models.BooleanField(default=False, help_text='Public case information visible to guests')
    is_archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_cases',
    )

    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.PROTECT,
        related_name='created_cases'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case_number']),
            models.Index(fields=['cnr_number']),
            models.Index(fields=['status']),
            models.Index(fields=['court']),
            models.Index(fields=['assigned_judge']),
            models.Index(fields=['assigned_lawyer']),
            models.Index(fields=['filing_date']),
            models.Index(fields=['next_hearing_date']),
            models.Index(fields=['case_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('can_view_all_cases', 'Can view all cases'),
            ('can_edit_case', 'Can edit case details'),
        ]

    def __str__(self):
        return f"{self.case_number} - {self.title}"

    @property
    def case_age_days(self):
        from datetime import date
        if not self.filing_date:
            return 0
        end = self.disposal_date or date.today()
        return (end - self.filing_date).days

    def change_status(self, new_status, actor, reason=''):
        """Transition status with validation + audit event."""
        if new_status == self.status:
            return False
        if not CaseStatus.is_valid_transition(self.status, new_status):
            raise ValueError(f"Invalid case status transition: {self.status} -> {new_status}")
        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        CaseStatusHistory.objects.create(
            case=self, from_status=old_status, to_status=new_status, changed_by=actor, reason=reason
        )
        return True


class CaseStatusOption(models.Model):
    """Configurable statuses (admin-managed extension points)."""
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    is_system = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.label})"


class CaseStatusHistory(models.Model):
    """Append-only history of case status transitions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=50)
    to_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, related_name='status_changes'
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['case', 'created_at'])]


class CaseParty(models.Model):
    """A party to a case. Supports multiple petitioners/respondents."""
    PARTY_TYPES = [
        ('petitioner', 'Petitioner'),
        ('respondent', 'Respondent'),
        ('applicant', 'Applicant'),
        ('opponent', 'Opponent'),
        ('intervenor', 'Intervenor'),
        ('third_party', 'Third Party'),
    ]
    PARTY_KINDS = [
        ('person', 'Person'),
        ('organization', 'Organization'),
        ('government', 'Government'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='parties')
    party_type = models.CharField(max_length=30, choices=PARTY_TYPES, db_index=True)
    party_kind = models.CharField(max_length=30, choices=PARTY_KINDS, default='person')
    name = models.CharField(max_length=255)
    representation = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    is_public = models.BooleanField(default=False, help_text='Expose minimal public info (name) to guests')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['party_type', 'name']
        indexes = [models.Index(fields=['case', 'party_type'])]

    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()}) - {self.case.case_number}"


class CaseLawyer(models.Model):
    """A lawyer associated with a case (beyond the single assigned_lawyer)."""
    ROLES = [
        ('lead', 'Lead Counsel'),
        ('co_counsel', 'Co-Counsel'),
        ('associate', 'Associate'),
        ('assistant', 'Assistant'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='case_lawyers')
    lawyer = models.ForeignKey(
        'authentication.User', on_delete=models.CASCADE, related_name='case_lawyer_links',
        limit_choices_to={'role': 'lawyer'}
    )
    role = models.CharField(max_length=30, choices=ROLES, default='associate')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['case', 'lawyer']
        indexes = [models.Index(fields=['lawyer', 'is_active'])]

    def __str__(self):
        return f"{self.lawyer.email} - {self.case.case_number}"


class CaseAssignment(models.Model):
    """Track lawyer assignments to cases (legacy-compatible)."""
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
    """Internal notes on cases."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on {self.case.case_number} by {self.author.email}"


class CaseEvent(models.Model):
    """
    Unified case timeline event. Generated from actual backend events
    (hearings, orders, documents, status changes), not hard-coded.
    """
    EVENT_TYPES = [
        ('CASE_FILED', 'Case Filed'),
        ('CASE_REGISTERED', 'Case Registered'),
        ('NOTICE_ISSUED', 'Notice Issued'),
        ('LAWYER_ASSIGNED', 'Lawyer Assigned'),
        ('HEARING_CREATED', 'Hearing Created'),
        ('HEARING_COMPLETED', 'Hearing Completed'),
        ('HEARING_ADJOURNED', 'Hearing Adjourned'),
        ('HEARING_RESCHEDULED', 'Hearing Rescheduled'),
        ('HEARING_CANCELLED', 'Hearing Cancelled'),
        ('DOCUMENT_UPLOADED', 'Document Uploaded'),
        ('ORDER_CREATED', 'Order Created'),
        ('ORDER_PUBLISHED', 'Order Published'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('CASE_TRANSFERRED', 'Case Transferred'),
        ('CASE_DISPOSED', 'Case Disposed'),
        ('PROCEEDING_RECORDED', 'Proceeding Recorded'),
        ('TASK_CREATED', 'Task Created'),
        ('TASK_COMPLETED', 'Task Completed'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_date = models.DateField(db_index=True)
    # Link to related entity for clickable timeline (nullable, polymorphic-ish via generic FK)
    content_type = models.ForeignKey(
        'contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    related_entity = models.CharField(max_length=100, blank=True, help_text='Human-readable target: Hearing #7, Order #2...')
    metadata = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-event_date', '-created_at']
        indexes = [
            models.Index(fields=['case', 'event_date']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"{self.case.case_number} - {self.get_event_type_display()} on {self.event_date}"
