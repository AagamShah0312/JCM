"""
Views for documents app
"""
from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import CaseDocument, DocumentVersion, DocumentExtraction
from .serializers import (
    CaseDocumentSerializer, DocumentVersionSerializer,
    DocumentExtractionSerializer, DocumentUploadSerializer
)
import os
import logging
from django.db.models import Q

logger = logging.getLogger(__name__)


class CaseDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for case document management"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['case', 'document_type']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return CaseDocument.objects.all()
        return CaseDocument.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        return CaseDocumentSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['admin', 'judge']:
            return Response({'error': 'Only admins and judges can upload documents'}, status=status.HTTP_403_FORBIDDEN)
        files = request.FILES.getlist('files') or request.FILES.getlist('file')
        if len(files) > 1:
            docs = self._save_documents(files)
            output = CaseDocumentSerializer(docs, many=True, context={'request': request}).data
            return Response(output, status=status.HTTP_201_CREATED)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = self._save_document(serializer)
        output = CaseDocumentSerializer(doc, context={'request': request}).data
        return Response(output, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can delete documents'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
    def _save_document(self, serializer):
        """Handle document upload"""
        file_obj = self.request.FILES.get('file')
        if file_obj:
            # Validate file type
            ext = os.path.splitext(file_obj.name)[1][1:].lower()
            allowed_types = ['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt']
            if ext not in allowed_types:
                raise serializers.ValidationError(f"File type .{ext} not allowed")
            
            # Validate file size (10MB limit)
            if file_obj.size > 10485760:
                raise serializers.ValidationError("File size exceeds 10MB limit")
        
        # Get case from request
        case_id = self.request.query_params.get('case') or self.request.data.get('case')
        case = self._get_case(case_id)
        self._check_upload_permission(case)
        
        doc = serializer.save(
            uploaded_by=self.request.user,
            case=case,
            file_size=file_obj.size if file_obj else 0,
            file_name=file_obj.name if file_obj else ''
        )
        self._extract_document(doc)
        
        logger.info(f"Document {doc.file_name} uploaded by {self.request.user.email}")
        return doc

    def _save_documents(self, files):
        case_id = self.request.query_params.get('case') or self.request.data.get('case')
        case = self._get_case(case_id)
        self._check_upload_permission(case)
        doc_types = self.request.data.getlist('document_types') if hasattr(self.request.data, 'getlist') else []
        descriptions = self.request.data.getlist('descriptions') if hasattr(self.request.data, 'getlist') else []
        uploaded = []
        for index, file_obj in enumerate(files):
            self._validate_file(file_obj)
            document_type = doc_types[index] if index < len(doc_types) and doc_types[index] else self.request.data.get('document_type', 'other')
            description = descriptions[index] if index < len(descriptions) and descriptions[index] else self.request.data.get('description', '')
            doc = CaseDocument.objects.create(
                case=case,
                document_type=document_type,
                file=file_obj,
                file_size=file_obj.size,
                file_name=file_obj.name,
                uploaded_by=self.request.user,
                description=description,
            )
            self._extract_document(doc)
            uploaded.append(doc)
        return uploaded

    def _validate_file(self, file_obj):
        ext = os.path.splitext(file_obj.name)[1][1:].lower()
        allowed_types = ['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt']
        if ext not in allowed_types:
            raise serializers.ValidationError(f"File type .{ext} not allowed")
        if file_obj.size > 10485760:
            raise serializers.ValidationError("File size exceeds 10MB limit")

    def _check_upload_permission(self, case):
        user = self.request.user
        if user.role == 'admin':
            return
        if user.role == 'judge' and (case.assigned_judge_id == user.id or case.created_by_id == user.id):
            return
        raise serializers.ValidationError("Only admins or the assigned judge can upload documents for this case")

    def _extract_document(self, doc):
        from apps.ai_assistant.services import DocumentProcessor
        try:
            text = DocumentProcessor.extract_text(doc.file.path)
            DocumentExtraction.objects.update_or_create(
                document=doc,
                defaults={'extracted_text': text, 'ocr_text': '', 'metadata': {'source': 'upload'}},
            )
        except Exception as exc:
            logger.warning(f"Document extraction failed for {doc.id}: {exc}")
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document"""
        document = self.get_object()
        if document.file:
            response = Response({
                'download_url': request.build_absolute_uri(document.file.url),
                'file_name': document.file_name
            })
            return response
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def extraction(self, request, pk=None):
        """Get document extraction/text"""
        document = self.get_object()
        try:
            extraction = document.extraction
            serializer = DocumentExtractionSerializer(extraction)
            return Response(serializer.data)
        except DocumentExtraction.DoesNotExist:
            return Response(
                {'message': 'Document extraction not available'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _get_case(self, case_id):
        from apps.cases.models import Case
        if case_id:
            try:
                return Case.objects.get(id=case_id)
            except Case.DoesNotExist:
                raise serializers.ValidationError("Case not found")
        raise serializers.ValidationError("Case ID is required")


class DocumentVersionViewSet(viewsets.ModelViewSet):
    """ViewSet for document versions"""
    
    queryset = DocumentVersion.objects.all()
    serializer_class = DocumentVersionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['document']
    ordering = ['-version_number']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return DocumentVersion.objects.all()
        return DocumentVersion.objects.filter(
            Q(document__case__assigned_lawyer=user) | Q(document__case__assignments__lawyer=user)
        ).distinct()
