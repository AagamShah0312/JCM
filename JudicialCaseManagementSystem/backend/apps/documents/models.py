"""
Documents app models: CaseDocument, DocumentVersion, DocumentExtraction,
DocumentAccess, DocumentChunk (enterprise document management).
"""
import hashlib
import uuid

from django.db import models
from django.core.validators import FileExtensionValidator


class DocumentProcessingState:
    UPLOADED = 'UPLOADED'
    PROCESSING = 'PROCESSING'
    PROCESSED = 'PROCESSED'
    OCR_REQUIRED = 'OCR_REQUIRED'
    OCR_COMPLETED = 'OCR_COMPLETED'
    FAILED = 'FAILED'

    CHOICES = [
        (UPLOADED, 'Uploaded'),
        (PROCESSING, 'Processing'),
        (PROCESSED, 'Processed'),
        (OCR_REQUIRED, 'OCR Required'),
        (OCR_COMPLETED, 'OCR Completed'),
        (FAILED, 'Failed'),
    ]


class DocumentVisibility:
    PUBLIC = 'PUBLIC'
    LAWYER_ONLY = 'LAWYER_ONLY'
    JUDGE_ONLY = 'JUDGE_ONLY'
    RESTRICTED = 'RESTRICTED'
    ADMIN_ONLY = 'ADMIN_ONLY'

    CHOICES = [
        (PUBLIC, 'Public'),
        (LAWYER_ONLY, 'Lawyers Only'),
        (JUDGE_ONLY, 'Judge Only'),
        (RESTRICTED, 'Restricted'),
        (ADMIN_ONLY, 'Admin Only'),
    ]


class DocumentState:
    ACTIVE = 'ACTIVE'
    ARCHIVED = 'ARCHIVED'
    SUPERSEDED = 'SUPERSEDED'
    DELETED = 'DELETED'

    CHOICES = [
        (ACTIVE, 'Active'),
        (ARCHIVED, 'Archived'),
        (SUPERSEDED, 'Superseded'),
        (DELETED, 'Deleted'),
    ]


class CaseDocument(models.Model):
    """Store case-related documents with enterprise metadata."""

    DOC_TYPES = [
        ('petition', 'Petition'),
        ('reply', 'Reply'),
        ('affidavit', 'Affidavit'),
        ('evidence', 'Evidence'),
        ('written_submission', 'Written Submission'),
        ('order', 'Order'),
        ('judgment', 'Judgment'),
        ('proceedings', 'Proceedings'),
        ('annexure', 'Annexure'),
        ('statement', 'Statement'),
        ('bonafide', 'Bonafide Document'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    hearing = models.ForeignKey(
        'hearings.Hearing',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text='Hearing this document is associated with, if any',
    )
    document_type = models.CharField(max_length=50, choices=DOC_TYPES, db_index=True)
    file_name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='case_documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt'])]
    )
    storage_key = models.CharField(max_length=500, blank=True, help_text='S3-compatible object key')
    file_size = models.BigIntegerField(default=0)  # in bytes
    mime_type = models.CharField(max_length=120, blank=True)
    checksum = models.CharField(max_length=64, blank=True, help_text='SHA-256 of the file')
    processing_state = models.CharField(
        max_length=30, choices=DocumentProcessingState.CHOICES, default=DocumentProcessingState.UPLOADED
    )
    processing_error = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20, choices=DocumentVisibility.CHOICES, default=DocumentVisibility.LAWYER_ONLY, db_index=True
    )
    state = models.CharField(max_length=20, choices=DocumentState.CHOICES, default=DocumentState.ACTIVE)
    uploaded_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['case', 'document_type']),
            models.Index(fields=['case', 'hearing']),
            models.Index(fields=['visibility']),
            models.Index(fields=['processing_state']),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.case.case_number}"

    def save(self, *args, **kwargs):
        if self.file and not self.checksum:
            try:
                self.file.seek(0)
                self.checksum = hashlib.sha256(self.file.read()).hexdigest()
                self.file.seek(0)
            except Exception:
                pass
        if self.file and not self.storage_key:
            self.storage_key = self.file.name
        super().save(*args, **kwargs)

    @property
    def is_public(self):
        return self.visibility == DocumentVisibility.PUBLIC


class DocumentVersion(models.Model):
    """Track document versions (append-only)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.IntegerField()
    file = models.FileField(upload_to='document_versions/%Y/%m/%d/')
    file_size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True)
    change_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']

    def __str__(self):
        return f"{self.document.file_name} - v{self.version_number}"


class DocumentExtraction(models.Model):
    """Store extracted text and metadata from documents."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='extraction'
    )
    extracted_text = models.TextField()
    ocr_text = models.TextField(blank=True)
    page_metadata = models.JSONField(default=dict, help_text='Per-page text/OCR info')
    metadata = models.JSONField(default=dict)
    extracted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Extraction for {self.document.file_name}"


class DocumentAccess(models.Model):
    """Explicit per-user document access grants (extensible permission model)."""
    ACCESS_LEVELS = [
        ('read', 'Read'),
        ('download', 'Download'),
        ('write', 'Write'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(CaseDocument, on_delete=models.CASCADE, related_name='access_grants')
    user = models.ForeignKey(
        'authentication.User', on_delete=models.CASCADE, related_name='document_access_grants'
    )
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='read')
    granted_by = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, related_name='granted_doc_access'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['document', 'user']
        indexes = [models.Index(fields=['user', 'access_level'])]

    def __str__(self):
        return f"{self.user.email} - {self.document.file_name} ({self.access_level})"


class DocumentChunk(models.Model):
    """Searchable chunks of a document, with optional pgvector embedding."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(CaseDocument, on_delete=models.CASCADE, related_name='chunks')
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='document_chunks')
    hearing = models.ForeignKey(
        'hearings.Hearing', on_delete=models.SET_NULL, null=True, blank=True, related_name='document_chunks'
    )
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    # pgvector embedding column added via migration (VectorField from pgvector.django)
    embedding = models.BinaryField(blank=True, null=True, help_text='Serialized pgvector embedding')
    embedding_model = models.CharField(max_length=200, blank=True)
    document_version = models.PositiveIntegerField(default=1)
    visibility = models.CharField(
        max_length=20, choices=DocumentVisibility.CHOICES, default=DocumentVisibility.LAWYER_ONLY
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['case']),
            models.Index(fields=['page_number']),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} p{self.page_number or '?'} - {self.document.file_name}"
