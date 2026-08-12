"""
Admin configuration for cases app
"""
from django.contrib import admin
from .models import (
    Case, CaseAssignment, CaseNote, CaseParty, CaseLawyer,
    CaseEvent, CaseStatusHistory, CaseStatusOption,
)


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['case_number', 'cnr_number', 'title', 'status', 'priority', 'court',
                    'filing_date', 'next_hearing_date', 'assigned_judge', 'assigned_lawyer']
    list_filter = ['status', 'priority', 'case_type', 'filing_date', 'is_public']
    search_fields = ['case_number', 'cnr_number', 'title', 'plaintiff_name', 'defendant_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ['case', 'event_type', 'title', 'event_date', 'created_by']
    list_filter = ['event_type', 'event_date']
    search_fields = ['case__case_number', 'title', 'description']
    readonly_fields = ['id', 'created_at']


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


@admin.register(CaseParty)
class CasePartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'case', 'party_type', 'party_kind', 'is_public']
    list_filter = ['party_type', 'party_kind', 'is_public']
    search_fields = ['name', 'case__case_number']


@admin.register(CaseLawyer)
class CaseLawyerAdmin(admin.ModelAdmin):
    list_display = ['lawyer', 'case', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['lawyer__email', 'case__case_number']


@admin.register(CaseStatusHistory)
class CaseStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['case', 'from_status', 'to_status', 'changed_by', 'created_at']
    list_filter = ['from_status', 'to_status']
    readonly_fields = ['id', 'created_at']


@admin.register(CaseStatusOption)
class CaseStatusOptionAdmin(admin.ModelAdmin):
    list_display = ['code', 'label', 'is_system', 'is_active']
