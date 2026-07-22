"""
Serializers for authentication app
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, LoginHistory
import re


class UserSerializer(serializers.ModelSerializer):
    """User serializer for API responses"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'professional_id', 'phone_number',
                  'profile_image', 'is_verified', 'created_at']
        read_only_fields = ['id', 'is_verified', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(required=True, max_length=150)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password', 'password_confirm']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        
        # Validate password strength
        password = data['password']
        if not re.search(r'[A-Z]', password):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'[0-9]', password):
            raise serializers.ValidationError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*]', password):
            raise serializers.ValidationError("Password must contain at least one special character")
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        username = validated_data['username'].strip()
        email = username if '@' in username else f'{username}@jcm.local'
        user = User(
            username=username,
            email=email.lower(),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='lawyer',
        )
        user.set_password(password)
        user.save()
        return user


class StaffCSVImportSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['admin', 'judge', 'lawyer'])
    file = serializers.FileField()


class RoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['role', 'professional_id', 'is_verified']


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        data['user'] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect'})
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match'})

        password = data['new_password']
        if not re.search(r'[A-Z]', password):
            raise serializers.ValidationError({'new_password': 'Password must contain at least one uppercase letter'})
        if not re.search(r'[0-9]', password):
            raise serializers.ValidationError({'new_password': 'Password must contain at least one digit'})
        if not re.search(r'[!@#$%^&*]', password):
            raise serializers.ValidationError({'new_password': 'Password must contain at least one special character'})
        return data


class LoginHistorySerializer(serializers.ModelSerializer):
    """Serializer for login history"""
    
    class Meta:
        model = LoginHistory
        fields = ['id', 'ip_address', 'user_agent', 'login_time', 'logout_time']
        read_only_fields = fields
