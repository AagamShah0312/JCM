"""
Orders app models: Order and OrderVersion.
"""
import uuid

from django.db import models


class Order(models.Model):
    """A judicial order (separate from generic documents)."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SIGNED', 'Signed'),
        ('PUBLISHED', 'Published'),
        ('SUPERSEDED', 'Superseded'),
    ]
    ORDER_TYPES = [
        ('INTERIM', 'Interim Order'),
        ('FINAL', 'Final Order'),
        ('JUDGMENT', 'Judgment'),
        ('DIRECTION', 'Direction'),
        ('ADJOURNMENT', 'Adjournment Order'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='orders')
    hearing = models.ForeignKey(
        'hearings.Hearing', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    order_number = models.CharField(max_length=50, blank=True)
    order_type = models.CharField(max_length=30, choices=ORDER_TYPES, default='INTERIM')
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    visibility = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', 'Public'),
            ('LAWYER_ONLY', 'Lawyers Only'),
            ('JUDGE_ONLY', 'Judge Only'),
            ('RESTRICTED', 'Restricted'),
            ('ADMIN_ONLY', 'Admin Only'),
        ],
        default='LAWYER_ONLY',
    )
    is_public = models.BooleanField(default=False, help_text='Visible to guest/public users')
    document = models.ForeignKey(
        'documents.CaseDocument', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='supersedes'
    )
    created_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, related_name='created_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['case', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_number or self.id} - {self.case.case_number}"


class OrderVersion(models.Model):
    """Version history for orders (append-only)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    document = models.ForeignKey(
        'documents.CaseDocument', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='order_versions'
    )
    content_text = models.TextField(blank=True)
    reason = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['order', 'version_number']

    def __str__(self):
        return f"{self.order} v{self.version_number}"
