"""
Views for documents app (enterprise): upload → pipeline, signed downloads,
version compare, visibility + access management.
"""
import hashlib
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import (
    CaseDocument, DocumentVersion, DocumentExtraction, DocumentAccess,
    DocumentProcessingState, DocumentVisibility,
)
from .serializers import (
    CaseDocumentSerializer, DocumentVersionSerializer, DocumentUploadSerializer,
    DocumentExtractionSerializer, DocumentCompareSerializer, GuestDocumentSerializer,
)
from apps.cases.permissions import (
    can_view_case, can_edit_case, can_view_document, can_download_document,
    case_queryset_for,
)
from apps.common.exceptions import NotFoundError, PermissionDeniedError, ValidationError_
from apps.audit.services import record_audit
import os

logger = logging.getLogger(__name__)


class CaseDocumentViewSet(viewsets.ModelViewSet):
    """Document management with async processing pipeline."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['case', 'document_type', 'visibility', 'processing_state', 'hearing']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return CaseDocument.objects.filter(visibility='PUBLIC', state='ACTIVE')
        if user.role == 'admin':
            return CaseDocument.objects.all()
        if user.role == 'guest':
            return CaseDocument.objects.filter(visibility='PUBLIC', state='ACTIVE')
        # Efficient: authorized docs via case set + explicit grants + own uploads
        from django.db.models import Q
        case_ids = case_queryset_for(user).values_list('id', flat=True)
        return CaseDocument.objects.filter(
            Q(case_id__in=case_ids, visibility__in=['PUBLIC', 'LAWYER_ONLY'])
            | Q(visibility='PUBLIC')
            | Q(uploaded_by=user)
            | Q(access_grants__user=user)
        ).distinct()

    def get_serializer_class(self):
        return CaseDocumentSerializer

    def get_object(self):
        doc = super().get_object()
        if not can_view_document(self.request.user, doc):
            raise NotFoundError('NOT_FOUND', 'Document not found')
        return doc

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['admin', 'judge']:
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins and judges can upload documents')

        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.cases.models import Case
        case = Case.objects.filter(id=data['case']).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found')
        if not can_edit_case(request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can upload documents for this case')

        files = data.get('files') or ([data['file']] if data.get('file') else [])
        if not files:
            raise ValidationError_('VALIDATION_ERROR', 'At least one file is required')

        doc_types = data.get('document_types') or []
        descriptions = data.get('descriptions') or []
        uploaded = []
        for index, file_obj in enumerate(files):
            self._validate_file(file_obj)
            document_type = doc_types[index] if index < len(doc_types) and doc_types[index] else data.get('document_type', 'other')
            description = descriptions[index] if index < len(descriptions) and descriptions[index] else data.get('description', '')

            doc = CaseDocument.objects.create(
                case=case,
                hearing_id=data.get('hearing'),
                document_type=document_type,
                file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size,
                mime_type=file_obj.content_type or '',
                checksum=self._checksum(file_obj),
                uploaded_by=request.user,
                description=description,
                visibility=data.get('visibility', DocumentVisibility.LAWYER_ONLY),
                processing_state=DocumentProcessingState.UPLOADED,
            )
            # Trigger async pipeline
            from .tasks import process_document_task
            process_document_task.delay(str(doc.id))
            # Refresh so eager-mode tasks are reflected in the response
            doc.refresh_from_db()

            # Timeline event
            from apps.cases.models import CaseEvent
            CaseEvent.objects.create(
                case=case,
                event_type='DOCUMENT_UPLOADED',
                title=f"Document uploaded: {doc.file_name}",
                description=description[:300],
                event_date=__import__('django.utils.timezone', fromlist=['now']).now().date(),
                created_by=request.user,
            )
            record_audit(user=request.user, action='DOCUMENT_UPLOADED', model_name='CaseDocument',
                         object_id=doc.id, changes={'file_name': doc.file_name},
                         ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
            uploaded.append(doc)

        output = CaseDocumentSerializer(uploaded, many=True, context={'request': request}).data
        return Response(output, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        doc = self.get_object()
        if request.user.role != 'admin':
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins can delete documents')
        # Soft-delete: preserve history (spec §56)
        doc.state = 'DELETED'
        doc.save(update_fields=['state', 'updated_at'])
        record_audit(user=request.user, action='DOCUMENT_DELETED', model_name='CaseDocument',
                     object_id=doc.id, changes={},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response({'message': 'Document deleted (archived)'}, status=status.HTTP_200_OK)

    @staticmethod
    def _validate_file(file_obj):
        ext = os.path.splitext(file_obj.name)[1][1:].lower()
        allowed = ['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt']
        if ext not in allowed:
            raise ValidationError_('INVALID_FILE_TYPE', f"File type .{ext} not allowed")
        if file_obj.size > 20 * 1024 * 1024:  # 20MB
            raise ValidationError_('FILE_TOO_LARGE', 'File size exceeds 20MB limit')

    @staticmethod
    def _checksum(file_obj):
        file_obj.seek(0)
        digest = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)
        return digest

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Authorized download: check perms, log, return signed URL."""
        doc = self.get_object()
        if not can_download_document(request.user, doc):
            raise PermissionDeniedError('PERMISSION_DENIED', 'You are not allowed to download this document')
        from services.storage import storage
        url = storage().signed_url(doc.storage_key or doc.file.name)
        record_audit(user=request.user, action='DOCUMENT_DOWNLOADED', model_name='CaseDocument',
                     object_id=doc.id, changes={},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                     request_id=getattr(request, 'request_id', ''))
        return Response({'download_url': url, 'file_name': doc.file_name})

    @action(detail=True, methods=['get'])
    def extraction(self, request, pk=None):
        doc = self.get_object()
        try:
            extraction = doc.extraction
        except DocumentExtraction.DoesNotExist:
            return Response({'message': 'Document extraction not available yet'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentExtractionSerializer(extraction).data)

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        doc = self.get_object()
        from .serializers import DocumentChunkSerializer
        serializer = DocumentChunkSerializer(doc.chunks.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        doc = self.get_object()
        serializer = DocumentVersionSerializer(doc.versions.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def new_version(self, request, pk=None):
        """Upload a new version (does NOT overwrite the original — spec §20)."""
        doc = self.get_object()
        if not can_edit_case(request.user, doc.case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can update documents')
        file_obj = request.FILES.get('file')
        if not file_obj:
            raise ValidationError_('VALIDATION_ERROR', 'file is required')
        self._validate_file(file_obj)
        last = doc.versions.order_by('-version_number').first()
        version_number = (last.version_number + 1) if last else 1
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=version_number,
            file=file_obj,
            file_size=file_obj.size,
            checksum=self._checksum(file_obj),
            uploaded_by=request.user,
            change_description=request.data.get('change_description', ''),
        )
        record_audit(user=request.user, action='DOCUMENT_VERSION_CREATED', model_name='DocumentVersion',
                     object_id=version.id, changes={'version_number': version_number},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response(DocumentVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def compare(self, request, pk=None):
        """Compare two versions (spec §40). Returns a machine diff + AI summary."""
        doc = self.get_object()
        serializer = DocumentCompareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v_a = doc.versions.filter(version_number=serializer.validated_data['version_a']).first()
        v_b = doc.versions.filter(version_number=serializer.validated_data['version_b']).first()
        if not v_a or not v_b:
            raise NotFoundError('NOT_FOUND', 'One or both versions not found')

        text_a = self._version_text(v_a)
        text_b = self._version_text(v_b)
        diff = self._simple_diff(text_a, text_b)

        # AI summary (advisory)
        ai_explanation = ''
        try:
            from apps.ai.services import compare_documents_ai
            result = compare_documents_ai(request.user, doc.case, v_a, v_b, diff['summary'])
            ai_explanation = result.get('explanation', '')
        except Exception as exc:
            logger.warning(f"AI comparison failed: {exc}")

        return Response({
            'version_a': v_a.version_number,
            'version_b': v_b.version_number,
            'diff': diff,
            'ai_explanation': ai_explanation,
            'warning': 'AI-generated comparison — verify against the actual documents.',
        })

    @staticmethod
    def _version_text(version):
        try:
            path = version.file.path
            from apps.ai_assistant.services import DocumentProcessor
            return DocumentProcessor.extract_text(path) or ''
        except Exception:
            return ''

    @staticmethod
    def _simple_diff(text_a, text_b):
        """Very small char/word-level diff summary (added/removed/modified)."""
        words_a = set(text_a.split())
        words_b = set(text_b.split())
        added = sorted(words_b - words_a)[:200]
        removed = sorted(words_a - words_b)[:200]
        modified = [w for w in added if w in removed]
        summary_lines = []
        if removed:
            summary_lines.append(f"Removed ({len(words_a - words_b)} unique words): {' '.join(removed[:50])}")
        if added:
            summary_lines.append(f"Added ({len(words_b - words_a)} unique words): {' '.join(added[:50])}")
        return {
            'added_words': list(added),
            'removed_words': list(removed),
            'summary': '\n'.join(summary_lines) or 'No significant word-level differences detected.',
        }

    @action(detail=True, methods=['post'])
    def grant_access(self, request, pk=None):
        """Explicit per-user document access grant (spec §19)."""
        doc = self.get_object()
        if request.user.role != 'admin':
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins can grant document access')
        user_id = request.data.get('user')
        access_level = request.data.get('access_level', 'read')
        from apps.authentication.models import User
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise NotFoundError('USER_NOT_FOUND', 'User not found')
        grant, created = DocumentAccess.objects.get_or_create(
            document=doc, user=user,
            defaults={'access_level': access_level, 'granted_by': request.user},
        )
        if not created:
            grant.access_level = access_level
            grant.save()
        from apps.audit.services import record_audit
        record_audit(user=request.user, action='PERMISSION_CHANGED', model_name='DocumentAccess',
                     object_id=grant.id, changes={'user': user.email, 'level': access_level},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        from .serializers import DocumentAccessSerializer
        return Response(DocumentAccessSerializer(grant).data)

    @action(detail=True, methods=['post'])
    def set_visibility(self, request, pk=None):
        """Change document visibility (spec §19, audited)."""
        doc = self.get_object()
        if not can_edit_case(request.user, doc.case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins or the assigned judge can change document visibility')
        visibility = request.data.get('visibility')
        if visibility not in dict(DocumentVisibility.CHOICES):
            raise ValidationError_('VALIDATION_ERROR', 'Invalid visibility value')
        old = doc.visibility
        doc.visibility = visibility
        doc.save(update_fields=['visibility', 'updated_at'])
        doc.chunks.update(visibility=visibility)
        record_audit(user=request.user, action='DOCUMENT_VISIBILITY_CHANGED', model_name='CaseDocument',
                     object_id=doc.id, changes={'from': old, 'to': visibility},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response(CaseDocumentSerializer(doc, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Re-run the document processing pipeline."""
        doc = self.get_object()
        if request.user.role not in ['admin', 'judge']:
            raise PermissionDeniedError('PERMISSION_DENIED')
        from .tasks import process_document_task
        process_document_task.delay(str(doc.id))
        doc.processing_state = DocumentProcessingState.UPLOADED
        doc.save(update_fields=['processing_state', 'updated_at'])
        return Response({'message': 'Document queued for reprocessing', 'processing_state': doc.processing_state})
