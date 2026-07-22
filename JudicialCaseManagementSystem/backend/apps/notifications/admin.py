"""
Admin configuration for notifications app
"""
from django.contrib import admin
from .models import Notification, NotificationSchedule


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title', 'message']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
    list_display = ['case', 'scheduled_date', 'notification_type', 'is_sent']
    list_filter = ['is_sent', 'scheduled_date']
    search_fields = ['case__case_number', 'message']
    readonly_fields = ['id', 'created_at']
