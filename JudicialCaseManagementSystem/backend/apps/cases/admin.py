"""
Admin configuration for cases app
"""
from django.contrib import admin
from .models import Case, CaseTimeline, CaseAssignment, CaseNote


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['case_number', 'title', 'status', 'court_name', 'filing_date', 
                    'next_hearing_date', 'assigned_lawyer']
    list_filter = ['status', 'court_name', 'case_type', 'filing_date']
    search_fields = ['case_number', 'title', 'plaintiff_name', 'defendant_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CaseTimeline)
class CaseTimelineAdmin(admin.ModelAdmin):
    list_display = ['case', 'event_type', 'event_date', 'created_by']
    list_filter = ['event_type', 'event_date']
    search_fields = ['case__case_number', 'event_description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CaseAssignment)
class CaseAssignmentAdmin(admin.ModelAdmin):
    list_display = ['case', 'lawyer', 'role', 'assigned_date', 'is_active']
    list_filter = ['role', 'is_active', 'assigned_date']
    search_fields = ['case__case_number', 'lawyer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CaseNote)
class CaseNoteAdmin(admin.ModelAdmin):
    list_display = ['case', 'author', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['case__case_number', 'author__email', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']
