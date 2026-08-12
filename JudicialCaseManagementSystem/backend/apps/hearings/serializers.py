"""
Serializers for hearings app (enterprise).
"""
from rest_framework import serializers
from .models import Hearing, HearingParticipant, HearingProceeding, AdjournmentReasonOption
from apps.authentication.serializers import UserSerializer


class AdjournmentReasonOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdjournmentReasonOption
        fields = ['id', 'code', 'label', 'is_active']


class HearingParticipantSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = HearingParticipant
        fields = ['id', 'hearing', 'user', 'user_details', 'name', 'role', 'status',
                  'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'hearing', 'created_at', 'updated_at']


class HearingProceedingSerializer(serializers.ModelSerializer):
    recorded_by_details = UserSerializer(source='recorded_by', read_only=True)
    documents = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source='documents_referenced'
    )

    class Meta:
        model = HearingProceeding
        fields = ['id', 'hearing', 'summary', 'notes', 'submissions', 'directions',
                  'attendance', 'documents', 'documents_referenced', 'next_action',
                  'next_hearing_date', 'recorded_by', 'recorded_by_details', 'is_public',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {'documents_referenced': {'write_only': True}}


class HearingSerializer(serializers.ModelSerializer):
    """Full hearing serializer (admin/judge/lawyer authorized)."""
    participants = HearingParticipantSerializer(many=True, read_only=True)
    proceedings = HearingProceedingSerializer(many=True, read_only=True)
    judge_details = UserSerializer(source='judge', read_only=True)
    courtroom_name = serializers.CharField(source='courtroom.name', read_only=True, default='')

    class Meta:
        model = Hearing
        fields = ['id', 'case', 'hearing_number', 'date', 'start_time', 'end_time',
                  'courtroom', 'courtroom_name', 'judge', 'judge_details', 'hearing_type',
                  'purpose', 'status', 'adjournment_reason', 'adjournment_note',
                  'next_hearing_date', 'next_hearing_notes', 'is_public',
                  'participants', 'proceedings', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'hearing_number', 'created_by', 'created_at', 'updated_at']


class GuestHearingSerializer(serializers.ModelSerializer):
    """Restricted hearing representation for guests."""
    judge_name = serializers.CharField(source='judge.get_full_name', read_only=True, default='')

    class Meta:
        model = Hearing
        fields = ['id', 'case', 'hearing_number', 'date', 'start_time', 'end_time',
                  'hearing_type', 'purpose', 'status', 'next_hearing_date', 'judge_name']
        read_only_fields = fields


class HearingCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    hearing_number = serializers.IntegerField(read_only=True)

    class Meta:
        model = Hearing
        fields = ['id', 'hearing_number', 'case', 'date', 'start_time', 'end_time',
                  'courtroom', 'judge', 'hearing_type', 'purpose', 'status', 'is_public',
                  'next_hearing_date', 'next_hearing_notes']
        extra_kwargs = {'case': {'required': True}}


class HearingRescheduleSerializer(serializers.Serializer):
    new_date = serializers.DateField()
    new_start_time = serializers.TimeField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
    adjournment_reason = serializers.CharField(required=False, allow_blank=True)
    adjournment_note = serializers.CharField(required=False, allow_blank=True)


class HearingCompleteSerializer(serializers.Serializer):
    """Mark a hearing completed + record proceedings in one call."""
    summary = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    submissions = serializers.CharField(required=False, allow_blank=True)
    directions = serializers.CharField(required=False, allow_blank=True)
    attendance = serializers.CharField(required=False, allow_blank=True)
    next_action = serializers.CharField(required=False, allow_blank=True)
    next_hearing_date = serializers.DateField(required=False)
    adjournment_reason = serializers.CharField(required=False, allow_blank=True)
    adjournment_note = serializers.CharField(required=False, allow_blank=True)
    documents = serializers.ListField(child=serializers.UUIDField(), required=False)
