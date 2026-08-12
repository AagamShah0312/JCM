"""
Serializers for documents app (enterprise).
"""
from rest_framework import serializers
from .models import (
    CaseDocument, DocumentVersion, DocumentExtraction, DocumentAccess, DocumentChunk,
)
from apps.authentication.serializers import UserSerializer


class DocumentExtractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentExtraction
        fields = ['id', 'extracted_text', 'ocr_text', 'page_metadata', 'metadata', 'extracted_at']
        read_only_fields = fields


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_details = UserSerializer(source='uploaded_by', read_only=True)

    class Meta:
        model = DocumentVersion
        fields = ['id', 'version_number', 'file', 'file_size', 'checksum', 'uploaded_by',
                  'uploaded_by_details', 'change_description', 'created_at']
        read_only_fields = ['id', 'version_number', 'file_size', 'checksum', 'created_at']


class DocumentAccessSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = DocumentAccess
        fields = ['id', 'document', 'user', 'user_details', 'access_level', 'granted_by', 'created_at']
        read_only_fields = ['id', 'granted_by', 'created_at']


class CaseDocumentSerializer(serializers.ModelSerializer):
    """Full document serializer (authorized users)."""
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    extraction = DocumentExtractionSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    access_grants = DocumentAccessSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = CaseDocument
        fields = ['id', 'case', 'hearing', 'document_type', 'file_name', 'file', 'file_size',
                  'mime_type', 'checksum', 'processing_state', 'processing_error', 'visibility',
                  'state', 'storage_key', 'uploaded_by', 'uploaded_by_email', 'description',
                  'uploaded_at', 'updated_at', 'extraction', 'versions', 'access_grants',
                  'file_url', 'download_url']
        read_only_fields = ['id', 'file_size', 'checksum', 'processing_state', 'processing_error',
                            'uploaded_at', 'updated_at']

    def get_file_url(self, obj):
        try:
            return obj.file.url
        except Exception:
            return ''

    def get_download_url(self, obj):
        """Authorized download URL (signed when storage is S3)."""
        from apps.cases.permissions import can_download_document
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not can_download_document(user, obj):
            return ''
        from services.storage import storage
        return storage().signed_url(obj.storage_key or obj.file.name)


class GuestDocumentSerializer(serializers.ModelSerializer):
    """Restricted document view for guests (public docs only)."""
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CaseDocument
        fields = ['id', 'case', 'document_type', 'file_name', 'description',
                  'uploaded_at', 'file_url']
        read_only_fields = fields

    def get_file_url(self, obj):
        try:
            return obj.file.url
        except Exception:
            return ''


class DocumentUploadSerializer(serializers.Serializer):
    """Multi-file upload (files + parallel document_types + descriptions)."""
    case = serializers.UUIDField()
    files = serializers.ListField(child=serializers.FileField(), required=False)
    file = serializers.FileField(required=False)
    document_types = serializers.ListField(child=serializers.CharField(), required=False)
    document_type = serializers.CharField(required=False, default='other')
    descriptions = serializers.ListField(child=serializers.CharField(), required=False)
    description = serializers.CharField(required=False, default='')
    hearing = serializers.UUIDField(required=False)
    visibility = serializers.ChoiceField(
        choices=[c[0] for c in [
            ('PUBLIC', 'Public'), ('LAWYER_ONLY', 'Lawyers Only'), ('JUDGE_ONLY', 'Judge Only'),
            ('RESTRICTED', 'Restricted'), ('ADMIN_ONLY', 'Admin Only'),
        ]],
        required=False, default='LAWYER_ONLY',
    )


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'document', 'chunk_index', 'page_number', 'text', 'embedding_model',
                  'document_version', 'visibility', 'created_at']
        read_only_fields = fields


class DocumentCompareSerializer(serializers.Serializer):
    """Compare two versions of a document."""
    version_a = serializers.IntegerField()
    version_b = serializers.IntegerField()
