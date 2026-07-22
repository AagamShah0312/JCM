"""
Admin configuration for documents app
"""
from django.contrib import admin
from .models import CaseDocument, DocumentVersion, DocumentExtraction


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'case', 'document_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['file_name', 'case__case_number']
    readonly_fields = ['id', 'uploaded_at', 'updated_at']


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'uploaded_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['document__file_name']
    readonly_fields = ['id', 'created_at']


@admin.register(DocumentExtraction)
class DocumentExtractionAdmin(admin.ModelAdmin):
    list_display = ['document', 'extracted_at']
    search_fields = ['document__file_name']
    readonly_fields = ['id', 'extracted_at']
