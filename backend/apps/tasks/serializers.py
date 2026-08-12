"""
Serializers for tasks app.
"""
from rest_framework import serializers
from .models import Task
from apps.authentication.serializers import UserSerializer


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_details = UserSerializer(source='assigned_to', read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'case', 'hearing', 'document',
                  'assigned_to', 'assigned_to_details', 'created_by', 'created_by_details',
                  'priority', 'status', 'due_date', 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'completed_at', 'created_at', 'updated_at']


class TaskCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'case', 'hearing', 'document',
                  'assigned_to', 'priority', 'status', 'due_date']
