"""
Serializers for courts app.
"""
from rest_framework import serializers
from .models import Court, Courtroom


class CourtroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Courtroom
        fields = ['id', 'court', 'name', 'floor', 'capacity', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CourtSerializer(serializers.ModelSerializer):
    courtrooms = CourtroomSerializer(many=True, read_only=True)

    class Meta:
        model = Court
        fields = ['id', 'name', 'court_type', 'state', 'city', 'address', 'is_active',
                  'courtrooms', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
