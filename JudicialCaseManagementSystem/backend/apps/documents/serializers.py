"""
Serializers for documents app
"""
from rest_framework import serializers
from .models import CaseDocument, DocumentVersion, DocumentExtraction


class DocumentExtractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentExtraction
        fields = ['id', 'extracted_text', 'ocr_text', 'metadata', 'extracted_at']
        read_only_fields = fields


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ['id', 'version_number', 'file', 'uploaded_by', 'change_description', 'created_at']
        read_only_fields = ['id', 'created_at']


class CaseDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    extraction = DocumentExtractionSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CaseDocument
        fields = ['id', 'case', 'document_type', 'file_name', 'file', 'file_size',
                  'uploaded_by', 'uploaded_by_email', 'description', 'uploaded_at',
                  'updated_at', 'extraction', 'versions', 'file_url']
        read_only_fields = ['id', 'file_size', 'uploaded_at', 'updated_at']

    def get_file_url(self, obj):
        try:
            return obj.file.url
        except Exception:
            return ''


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseDocument
        fields = ['case', 'document_type', 'file', 'description']
