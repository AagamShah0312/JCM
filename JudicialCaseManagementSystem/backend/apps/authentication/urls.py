"""
URL routing for authentication app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, UserViewSet, ChangePasswordView,
    StaffCSVPreviewView, StaffCSVImportConfirmView,
    CaseCSVPreviewView, CaseCSVImportConfirmView,
    CSVErrorReportView, TwoFactorStatusView, TwoFactorEnrollView,
    TwoFactorVerifyView, TwoFactorDisableView, TwoFactorChallengeView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('mfa/status/', TwoFactorStatusView.as_view(), name='mfa-status'),
    path('mfa/enroll/', TwoFactorEnrollView.as_view(), name='mfa-enroll'),
    path('mfa/verify/', TwoFactorVerifyView.as_view(), name='mfa-verify'),
    path('mfa/disable/', TwoFactorDisableView.as_view(), name='mfa-disable'),
    path('mfa/challenge/', TwoFactorChallengeView.as_view(), name='mfa-challenge'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('csv/staff/preview/', StaffCSVPreviewView.as_view(), name='staff-csv-preview'),
    path('csv/staff/import/', StaffCSVImportConfirmView.as_view(), name='staff-csv-import'),
    path('csv/cases/preview/', CaseCSVPreviewView.as_view(), name='cases-csv-preview'),
    path('csv/cases/import/', CaseCSVImportConfirmView.as_view(), name='cases-csv-import'),
    path('csv/error-report/', CSVErrorReportView.as_view(), name='csv-error-report'),
    path('', include(router.urls)),
]
