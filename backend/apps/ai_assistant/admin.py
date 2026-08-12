"""
Admin configuration for AI assistant app
"""
from django.contrib import admin
from .models import AIConversation, AIMessage, AIQuery, DocumentEmbedding


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'case', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'case__case_number']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'tokens_used', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content']
    readonly_fields = ['id', 'created_at']


@admin.register(AIQuery)
class AIQueryAdmin(admin.ModelAdmin):
    list_display = ['user', 'case', 'query_type', 'success', 'processing_time', 'created_at']
    list_filter = ['query_type', 'success', 'created_at']
    search_fields = ['user__email', 'case__case_number', 'query_text']
    readonly_fields = ['id', 'created_at']


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['document', 'embedding_model', 'chunk_count', 'processed_at']
    list_filter = ['processed_at']
    search_fields = ['document__file_name']
    readonly_fields = ['id', 'processed_at']
