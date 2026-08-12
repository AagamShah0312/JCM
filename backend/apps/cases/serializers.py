"""
Serializers for cases app (enterprise version).
"""
from rest_framework import serializers
from apps.authentication.serializers import UserSerializer
from .models import (
    Case, CaseEvent, CaseAssignment, CaseNote, CaseParty, CaseLawyer,
    CaseStatusHistory, CaseStatusOption,
)


class CaseEventSerializer(serializers.ModelSerializer):
    """Serializer for case timeline events (unified event log)."""

    created_by_details = UserSerializer(source='created_by', read_only=True)

    class Meta:
        model = CaseEvent
        fields = ['id', 'case', 'event_type', 'title', 'description', 'event_date',
                  'content_type', 'object_id', 'related_entity', 'metadata',
                  'created_by', 'created_by_details', 'created_at']
        read_only_fields = ['id', 'case', 'created_at']


class CaseAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for case assignments"""

    lawyer_details = UserSerializer(source='lawyer', read_only=True)

    class Meta:
        model = CaseAssignment
        fields = ['id', 'case', 'lawyer', 'lawyer_details', 'assigned_date', 'role',
                  'is_active', 'created_at', 'updated_at']
        # 'case' is injected by the view (e.g. /cases/{id}/assign_lawyer/).
        read_only_fields = ['id', 'case', 'assigned_date', 'created_at', 'updated_at']


class CaseNoteSerializer(serializers.ModelSerializer):
    """Serializer for case notes"""

    author_details = UserSerializer(source='author', read_only=True)

    class Meta:
        model = CaseNote
        fields = ['id', 'case', 'author', 'author_details', 'content', 'is_public',
                  'created_at', 'updated_at']
        # 'case' is injected by the view (e.g. POST /cases/{id}/notes/).
        read_only_fields = ['id', 'case', 'created_at', 'updated_at']


class CasePartySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseParty
        fields = ['id', 'case', 'party_type', 'party_kind', 'name', 'representation',
                  'contact_email', 'contact_phone', 'address', 'is_public', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CaseLawyerSerializer(serializers.ModelSerializer):
    lawyer_details = UserSerializer(source='lawyer', read_only=True)

    class Meta:
        model = CaseLawyer
        fields = ['id', 'case', 'lawyer', 'lawyer_details', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'case', 'created_at', 'updated_at']


class CaseStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_details = UserSerializer(source='changed_by', read_only=True)

    class Meta:
        model = CaseStatusHistory
        fields = ['id', 'from_status', 'to_status', 'changed_by', 'changed_by_details',
                  'reason', 'created_at']
        read_only_fields = ['id', 'created_at']


class CaseStatusOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseStatusOption
        fields = ['id', 'code', 'label', 'is_system', 'is_active']


# ---------------------------------------------------------------------------
# Role-specific case serializers (spec §69)
# ---------------------------------------------------------------------------


class GuestCaseSerializer(serializers.ModelSerializer):
    """Restricted representation for guest/public users."""
    court_name = serializers.CharField(source='court.name', read_only=True, default='')

    class Meta:
        model = Case
        fields = ['id', 'case_number', 'cnr_number', 'title', 'status', 'case_type',
                  'court_name', 'filing_date', 'next_hearing_date', 'priority',
                  'subject', 'category', 'public_interest_link']
        read_only_fields = fields


class LawyerCaseSerializer(serializers.ModelSerializer):
    """Representation for lawyers (no internal judge notes)."""

    class Meta:
        model = Case
        fields = ['id', 'case_number', 'cnr_number', 'title', 'status', 'case_type',
                  'court_name', 'filing_date', 'registration_date', 'next_hearing_date',
                  'priority', 'subject', 'category', 'plaintiff_name', 'defendant_name',
                  'assigned_judge', 'assigned_lawyer', 'public_interest_link',
                  'disposal_date', 'disposal_reason', 'created_at', 'updated_at']
        read_only_fields = fields


class JudgeCaseSerializer(serializers.ModelSerializer):
    """Representation for judges."""

    class Meta:
        model = Case
        fields = ['id', 'case_number', 'cnr_number', 'title', 'status', 'case_type',
                  'court_name', 'filing_date', 'registration_date', 'next_hearing_date',
                  'priority', 'subject', 'category', 'plaintiff_name', 'defendant_name',
                  'assigned_judge', 'assigned_lawyer', 'public_interest_link',
                  'disposal_date', 'disposal_reason', 'created_at', 'updated_at',
                  'description']
        read_only_fields = fields


class AdminCaseSerializer(serializers.ModelSerializer):
    """Full representation for admins."""

    class Meta:
        model = Case
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Legacy-compatible serializers
# ---------------------------------------------------------------------------


class CaseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for case listings"""
    is_bookmarked = serializers.SerializerMethodField()
    assigned_judge_details = UserSerializer(source='assigned_judge', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True, default='')

    class Meta:
        model = Case
        fields = ['id', 'case_number', 'title', 'status', 'priority', 'next_hearing_date',
                  'plaintiff_name', 'defendant_name', 'assigned_judge', 'assigned_judge_details',
                  'court_name', 'public_interest_link', 'created_at', 'is_bookmarked']

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or user.role != 'lawyer':
            return False
        return obj.assignments.filter(lawyer=user, is_active=True).exists() or obj.assigned_lawyer_id == user.id


class CaseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for case objects"""

    created_by_details = UserSerializer(source='created_by', read_only=True)
    assigned_lawyer_details = UserSerializer(source='assigned_lawyer', read_only=True)
    assigned_judge_details = UserSerializer(source='assigned_judge', read_only=True)
    timeline_events = CaseEventSerializer(source='events', many=True, read_only=True)
    assignments = CaseAssignmentSerializer(many=True, read_only=True)
    parties = CasePartySerializer(many=True, read_only=True)
    case_lawyers = CaseLawyerSerializer(many=True, read_only=True)
    status_history = CaseStatusHistorySerializer(many=True, read_only=True)
    notes_count = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['id', 'case_number', 'cnr_number', 'title', 'description', 'court_name',
                  'court', 'courtroom', 'case_type', 'priority', 'filing_date',
                  'registration_date', 'next_hearing_date', 'status', 'judge_name',
                  'assigned_judge', 'assigned_judge_details', 'public_interest_link',
                  'plaintiff_name', 'defendant_name', 'created_by', 'created_by_details',
                  'assigned_lawyer', 'assigned_lawyer_details', 'timeline_events',
                  'assignments', 'parties', 'case_lawyers', 'status_history',
                  'notes_count', 'subject', 'category', 'disposal_date', 'disposal_reason',
                  'is_public', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_notes_count(self, obj):
        return obj.notes.count()


class CaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cases"""

    class Meta:
        model = Case
        fields = ['title', 'description', 'court_name', 'court', 'courtroom', 'case_type',
                  'filing_date', 'registration_date', 'next_hearing_date', 'status',
                  'judge_name', 'assigned_judge', 'public_interest_link', 'priority',
                  'subject', 'category', 'plaintiff_name', 'defendant_name', 'assigned_lawyer']
        extra_kwargs = {
            'assigned_lawyer': {'required': False, 'allow_null': True},
            'assigned_judge': {'required': False, 'allow_null': True},
            'court': {'required': False, 'allow_null': True},
            'courtroom': {'required': False, 'allow_null': True},
        }

    def validate(self, data):
        filing_date = data.get('filing_date', getattr(self.instance, 'filing_date', None))
        next_hearing_date = data.get('next_hearing_date', getattr(self.instance, 'next_hearing_date', None))
        if next_hearing_date:
            from django.utils import timezone
            today = timezone.now().date()
            if next_hearing_date < today:
                raise serializers.ValidationError({'next_hearing_date': 'Next hearing date cannot be in the past'})
            if filing_date and next_hearing_date < filing_date:
                raise serializers.ValidationError({'next_hearing_date': 'Next hearing date cannot be before filing date'})
        assigned_judge = data.get('assigned_judge', getattr(self.instance, 'assigned_judge', None))
        assigned_lawyer = data.get('assigned_lawyer', getattr(self.instance, 'assigned_lawyer', None))
        if assigned_judge and assigned_judge.role != 'judge':
            raise serializers.ValidationError({'assigned_judge': 'Selected user must be a judge'})
        if assigned_lawyer and assigned_lawyer.role != 'lawyer':
            raise serializers.ValidationError({'assigned_lawyer': 'Selected user must be a lawyer'})
        return data


class CaseCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Case
        fields = ['id', 'case_number', 'cnr_number', 'title', 'description', 'court_name',
                  'court', 'courtroom', 'case_type', 'filing_date', 'registration_date',
                  'next_hearing_date', 'status', 'judge_name', 'assigned_judge',
                  'public_interest_link', 'priority', 'subject', 'category',
                  'plaintiff_name', 'defendant_name', 'assigned_lawyer']
        extra_kwargs = {
            'assigned_lawyer': {'required': False, 'allow_null': True},
            'assigned_judge': {'required': False, 'allow_null': True},
            'court': {'required': False, 'allow_null': True},
            'courtroom': {'required': False, 'allow_null': True},
            'cnr_number': {'required': False, 'allow_null': True},
            'status': {'required': False},
        }

    def validate(self, data):
        next_hearing_date = data.get('next_hearing_date')
        filing_date = data.get('filing_date')
        if next_hearing_date:
            from django.utils import timezone
            today = timezone.now().date()
            if next_hearing_date < today:
                raise serializers.ValidationError({'next_hearing_date': 'Next hearing date cannot be in the past'})
            if filing_date and next_hearing_date < filing_date:
                raise serializers.ValidationError({'next_hearing_date': 'Next hearing date cannot be before filing date'})
        assigned_judge = data.get('assigned_judge')
        assigned_lawyer = data.get('assigned_lawyer')
        if assigned_judge and assigned_judge.role != 'judge':
            raise serializers.ValidationError({'assigned_judge': 'Selected user must be a judge'})
        if assigned_lawyer and assigned_lawyer.role != 'lawyer':
            raise serializers.ValidationError({'assigned_lawyer': 'Selected user must be a lawyer'})
        return data
