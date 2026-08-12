"""
Django models for authentication app
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    """Custom User model with role-based access control"""
    
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('judge', 'Judge'),
        ('lawyer', 'Lawyer'),
        ('guest', 'Guest'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='lawyer')
    professional_id = models.CharField(max_length=80, unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class TokenBlacklist(models.Model):
    """Store blacklisted JWT tokens"""
    
    token = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blacklisted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Token Blacklist'
    
    def __str__(self):
        return f"Blacklisted token for {self.user.email}"


class LoginHistory(models.Model):
    """Track user login activity"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time}"


class JudgeProfile(models.Model):
    """Professional profile for a judge."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='judge_profile')
    designation = models.CharField(max_length=150, blank=True)
    court = models.ForeignKey(
        'courts.Court', on_delete=models.SET_NULL, null=True, blank=True, related_name='judges'
    )
    default_courtroom = models.ForeignKey(
        'courts.Courtroom', on_delete=models.SET_NULL, null=True, blank=True, related_name='presiding_judges'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} ({self.designation})"


class LawyerProfile(models.Model):
    """Professional profile for a lawyer."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lawyer_profile')
    bar_registration_number = models.CharField(max_length=100, blank=True)
    bar_council = models.CharField(max_length=150, blank=True)
    firm_name = models.CharField(max_length=200, blank=True)
    practice_area = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} ({self.bar_registration_number})"


class TwoFactorAuth(models.Model):
    """
    MFA-ready hook (spec §46). The platform ships with the data model and
    verification interface; the actual TOTP/WebAuthn provider is pluggable
    (e.g. django-otp, pyotp + qrcode). When MFA is enabled for a user, a
    challenge is required after password authentication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    is_enabled = models.BooleanField(default=False)
    provider = models.CharField(
        max_length=30,
        choices=[
            ('totp', 'TOTP (authenticator app)'),
            ('webauthn', 'WebAuthn / Passkey'),
            ('sms', 'SMS OTP'),
            ('email', 'Email OTP'),
        ],
        default='totp',
    )
    secret_encrypted = models.TextField(blank=True, help_text='Provider secret (encrypted at rest)')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'is_enabled'])]

    def __str__(self):
        return f"2FA {'enabled' if self.is_enabled else 'disabled'} for {self.user.email}"
