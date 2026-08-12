"""
Admin configuration for authentication app
"""
from django.contrib import admin
from .models import User, TokenBlacklist, LoginHistory


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_verified', 'created_at']
    list_filter = ['role', 'is_verified', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(TokenBlacklist)
class TokenBlacklistAdmin(admin.ModelAdmin):
    list_display = ['user', 'blacklisted_at']
    search_fields = ['user__email']
    readonly_fields = ['blacklisted_at']


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_time', 'logout_time']
    list_filter = ['login_time']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['login_time']
