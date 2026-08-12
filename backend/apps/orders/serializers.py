"""
Serializers for orders app.
"""
from rest_framework import serializers
from .models import Order, OrderVersion
from apps.authentication.serializers import UserSerializer


class OrderVersionSerializer(serializers.ModelSerializer):
    uploaded_by_details = UserSerializer(source='uploaded_by', read_only=True)

    class Meta:
        model = OrderVersion
        fields = ['id', 'version_number', 'document', 'content_text', 'reason',
                  'uploaded_by', 'uploaded_by_details', 'created_at']
        read_only_fields = ['id', 'version_number', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    versions = OrderVersionSerializer(many=True, read_only=True)
    judge_details = UserSerializer(source='created_by', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'case', 'hearing', 'order_number', 'order_type', 'title',
                  'summary', 'date', 'status', 'visibility', 'is_public', 'document',
                  'published_at', 'superseded_by', 'versions', 'judge_details',
                  'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'published_at', 'created_by', 'created_at', 'updated_at']


class GuestOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'case', 'order_number', 'order_type', 'title', 'date', 'status']
        read_only_fields = fields


class OrderCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'case', 'hearing', 'order_type', 'title', 'summary', 'date',
                  'status', 'visibility', 'is_public', 'document']
        extra_kwargs = {
            'case': {'required': True},
            'date': {'required': True},
            'status': {'required': False, 'default': 'DRAFT'},
        }
