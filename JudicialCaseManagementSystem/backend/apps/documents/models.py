"""
Django models for documents app
"""
from django.db import models
from django.core.validators import FileExtensionValidator
import uuid


class CaseDocument(models.Model):
    """Store case-related documents"""
    
    DOC_TYPES = (
        ('petition', 'Petition'),
        ('affidavit', 'Affidavit'),
        ('judgment', 'Judgment'),
        ('order', 'Order'),
        ('evidence', 'Evidence'),
        ('statement', 'Statement'),
        ('bonafide', 'Bonafide Document'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=50, choices=DOC_TYPES)
    file_name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='case_documents/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt'])]
    )
    file_size = models.BigIntegerField()  # in bytes
    uploaded_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['case', 'document_type']),
        ]
    
    def __str__(self):
        return f"{self.file_name} - {self.case.case_number}"


class DocumentVersion(models.Model):
    """Track document versions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.IntegerField()
    file = models.FileField(upload_to='document_versions/%Y/%m/%d/')
    uploaded_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True)
    change_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.file_name} - v{self.version_number}"


class DocumentExtraction(models.Model):
    """Store extracted text and metadata from documents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        CaseDocument,
        on_delete=models.CASCADE,
        related_name='extraction'
    )
    extracted_text = models.TextField()
    ocr_text = models.TextField(blank=True)  # OCR'd text for scanned documents
    metadata = models.JSONField(default=dict)  # Author, date, keywords, etc.
    extracted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Extraction for {self.document.file_name}"
