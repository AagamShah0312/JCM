"""
Permission classes for cases app
"""
from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Allow write access only to admins"""
    
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.role == 'admin'


class IsLawyerOrAdmin(BasePermission):
    """Allow access to lawyers and admins"""
    
    def has_permission(self, request, view):
        return request.user and request.user.role in ['lawyer', 'admin']
