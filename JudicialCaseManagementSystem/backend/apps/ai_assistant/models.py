"""
Django models for AI assistant app
"""
from django.db import models
import uuid


class AIConversation(models.Model):
    """Store AI chat conversations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='ai_conversations'
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='ai_conversations'
    )
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation for {self.case.case_number} by {self.user.email}"


class AIMessage(models.Model):
    """Individual messages in AI conversations"""
    
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    tokens_used = models.IntegerField(default=0)
    sources = models.JSONField(default=list)  # Store referenced documents
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class DocumentEmbedding(models.Model):
    """Store document embeddings for RAG"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        'documents.CaseDocument',
        on_delete=models.CASCADE,
        related_name='embedding'
    )
    embedding_vector = models.BinaryField()  # Store as binary for efficiency
    embedding_model = models.CharField(max_length=100, default='sentence-transformers/all-MiniLM-L6-v2')
    chunk_count = models.IntegerField(default=0)
    processed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Embedding for {self.document.file_name}"


class AIQuery(models.Model):
    """Track AI queries for analytics and improvement"""
    
    QUERY_TYPES = (
        ('explain', 'Explain Case'),
        ('summarize', 'Summarize'),
        ('timeline', 'Timeline Generation'),
        ('qa', 'Question Answering'),
        ('search', 'Document Search'),
        ('analysis', 'Legal Analysis'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='ai_queries'
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='ai_queries'
    )
    query_type = models.CharField(max_length=50, choices=QUERY_TYPES)
    query_text = models.TextField()
    response = models.TextField()
    tokens_used = models.IntegerField(default=0)
    processing_time = models.FloatField()  # in seconds
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.query_type} - {self.query_text[:50]}"
