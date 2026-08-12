"""
Serializers for notifications app
"""
from rest_framework import serializers
from .models import Notification, NotificationSchedule


class NotificationSerializer(serializers.ModelSerializer):
    case_number = serializers.CharField(source='case.case_number', read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'case', 'case_number',
                  'is_read', 'action_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationScheduleSerializer(serializers.ModelSerializer):
    case_number = serializers.CharField(source='case.case_number', read_only=True)
    
    class Meta:
        model = NotificationSchedule
        fields = ['id', 'case', 'case_number', 'scheduled_date', 'scheduled_time',
                  'notification_type', 'message', 'recipients', 'is_sent', 'sent_at']
        read_only_fields = ['id', 'is_sent', 'sent_at']
