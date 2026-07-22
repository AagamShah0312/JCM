"""
Serializers for AI assistant app
"""
from rest_framework import serializers
from .models import AIConversation, AIMessage, AIQuery


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ['id', 'role', 'content', 'tokens_used', 'sources', 'created_at']
        read_only_fields = fields


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)
    case_number = serializers.CharField(source='case.case_number', read_only=True)
    case_title = serializers.CharField(source='case.title', read_only=True)
    
    class Meta:
        model = AIConversation
        fields = ['id', 'user', 'case', 'case_number', 'case_title', 'title', 'messages',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AIMessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField()


class AIQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIQuery
        fields = ['id', 'user', 'case', 'query_type', 'query_text', 'response',
                  'tokens_used', 'processing_time', 'success', 'error_message', 'created_at']
        read_only_fields = fields
