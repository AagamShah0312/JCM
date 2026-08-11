"""
Serializers for cases app
"""
from rest_framework import serializers
from apps.authentication.serializers import UserSerializer
from .models import Case, CaseTimeline, CaseAssignment, CaseNote


class CaseTimelineSerializer(serializers.ModelSerializer):
    """Serializer for case timeline events"""
    
    created_by_details = UserSerializer(source='created_by', read_only=True)
    
    class Meta:
        model = CaseTimeline
        fields = ['id', 'case', 'event_type', 'event_description', 'event_date', 
                  'notes', 'created_by', 'created_by_details', 'created_at', 'updated_at']
        # 'case' is injected by the view (e.g. /cases/{id}/add_timeline_event/),
        # so it must not be required from the request payload.
        read_only_fields = ['id', 'case', 'created_at', 'updated_at']


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


class CaseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for case listings"""
    is_bookmarked = serializers.SerializerMethodField()
    assigned_judge_details = UserSerializer(source='assigned_judge', read_only=True)
    
    class Meta:
        model = Case
        fields = ['id', 'case_number', 'title', 'status', 'next_hearing_date', 
                  'plaintiff_name', 'defendant_name', 'assigned_judge', 'assigned_judge_details',
                  'public_interest_link', 'created_at', 'is_bookmarked']

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
    timeline_events = CaseTimelineSerializer(many=True, read_only=True)
    assignments = CaseAssignmentSerializer(many=True, read_only=True)
    notes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Case
        fields = ['id', 'case_number', 'title', 'description', 'court_name', 'case_type',
                  'filing_date', 'next_hearing_date', 'status', 'judge_name', 
                  'assigned_judge', 'assigned_judge_details', 'public_interest_link',
                  'plaintiff_name', 'defendant_name', 'created_by', 'created_by_details',
                  'assigned_lawyer', 'assigned_lawyer_details', 'timeline_events',
                  'assignments', 'notes_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_notes_count(self, obj):
        return obj.notes.count()


class CaseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cases"""
    
    class Meta:
        model = Case
        fields = ['title', 'description', 'court_name', 'case_type', 'filing_date',
                  'next_hearing_date', 'status', 'judge_name', 'assigned_judge',
                  'public_interest_link', 'plaintiff_name', 'defendant_name', 'assigned_lawyer']
        extra_kwargs = {
            'assigned_lawyer': {'required': False, 'allow_null': True},
            'assigned_judge': {'required': False, 'allow_null': True},
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
        fields = ['id', 'case_number', 'title', 'description', 'court_name', 'case_type',
                  'filing_date', 'next_hearing_date', 'status', 'judge_name', 'assigned_judge',
                  'public_interest_link',
                  'plaintiff_name', 'defendant_name', 'assigned_lawyer']
        extra_kwargs = {
            'assigned_lawyer': {'required': False, 'allow_null': True},
            'assigned_judge': {'required': False, 'allow_null': True},
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
