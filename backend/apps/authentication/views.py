"""
Views for authentication app
"""
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import User, LoginHistory
from .serializers import (
    UserSerializer, UserRegistrationSerializer, 
    UserLoginSerializer, LoginHistorySerializer, ChangePasswordSerializer,
    StaffCSVImportSerializer, RoleUpdateSerializer
)
from apps.cases.models import Case
from django.db.models import Q
import csv
import io
import logging

logger = logging.getLogger(__name__)


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """User login endpoint with JWT token generation"""
    
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Record login history
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        try:
            LoginHistory.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as exc:
            logger.warning(f"LoginHistory write failed for {user.email}: {exc}")

        # MFA challenge (spec §46): if 2FA is enabled, require a code before
        # issuing JWTs. Password verification already succeeded above.
        from .mfa import is_mfa_available, is_mfa_enabled, issue_mfa_challenge
        if is_mfa_available() and is_mfa_enabled(user):
            challenge = issue_mfa_challenge(user)
            logger.info(f"User {user.email} passed password step; MFA challenge issued")
            return Response({
                'mfa_required': True,
                'mfa_token': challenge,
                'user': UserSerializer(user).data,
            }, status=status.HTTP_200_OK)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        logger.info(f"User {user.email} logged in from {ip_address}")
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '0.0.0.0'


class UserLogoutView(generics.GenericAPIView):
    """User logout endpoint"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logger.info(f"User {request.user.email} logged out")
            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management"""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['promote_demote', 'partial_update', 'update']:
            return RoleUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        # Users can only see their own profile unless they're admin
        if self.request.user.role == 'admin':
            return User.objects.all()
        if self.request.user.role in ['judge', 'lawyer', 'guest']:
            return User.objects.filter(role__in=['judge', 'lawyer']).order_by('role', 'professional_id', 'email')
        return User.objects.filter(id=self.request.user.id)

    def update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can promote or demote users'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can promote or demote users'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def import_staff_csv(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can import staff CSV files'}, status=status.HTTP_403_FORBIDDEN)

        serializer = StaffCSVImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data['role']
        uploaded = serializer.validated_data['file']
        text = uploaded.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))

        created = 0
        updated = 0
        rows = []
        for row in reader:
            professional_id = (row.get('professional_id') or row.get('id') or row.get('unique_id') or '').strip()
            email = (row.get('email') or '').strip().lower()
            if not professional_id or not email:
                rows.append({'email': email, 'professional_id': professional_id, 'status': 'skipped'})
                continue

            defaults = {
                'username': (row.get('username') or email).strip(),
                'first_name': (row.get('first_name') or row.get('name') or '').strip(),
                'last_name': (row.get('last_name') or '').strip(),
                'role': role,
                'professional_id': professional_id or None,
                'is_verified': True,
            }
            user, was_created = User.objects.update_or_create(email=email, defaults=defaults)
            raw_password = (row.get('password') or row.get('Password') or '').strip()
            if raw_password:
                user.set_password(raw_password)
                user.save(update_fields=['password'])
            elif was_created:
                user.set_unusable_password()
                user.save(update_fields=['password'])
                created += 1
                row_status = 'created'
            else:
                updated += 1
                row_status = 'updated'
            rows.append({'id': str(user.id), 'email': user.email, 'professional_id': user.professional_id, 'status': row_status})

        return Response({'created': created, 'updated': updated, 'rows': rows}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def promote_demote(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({'error': 'Only admins can promote or demote users'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        serializer = RoleUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        profile = self.get_object()
        if request.user.role != 'admin' and request.user != profile and request.user.role not in ['judge', 'lawyer', 'guest']:
            return Response({'error': 'You do not have permission to view analytics'}, status=status.HTTP_403_FORBIDDEN)

        if profile.role == 'judge':
            queryset = Case.objects.filter(assigned_judge=profile)
        elif profile.role == 'lawyer':
            queryset = Case.objects.filter(assigned_lawyer=profile) | Case.objects.filter(assignments__lawyer=profile)
            queryset = queryset.distinct()
        else:
            queryset = Case.objects.none()

        total = queryset.count()
        closed = queryset.filter(status='closed').count()
        active = queryset.filter(status__in=['pending', 'active', 'postponed', 'appealed']).count()
        winner_name = profile.get_full_name() or profile.email
        won = queryset.filter(
            Q(notes__content__icontains='winner') &
            Q(notes__content__icontains=winner_name)
        ).distinct().count()
        win_percentage = round((won / closed) * 100, 2) if closed else 0
        recent_cases = queryset.order_by('-created_at')[:10]
        return Response({
            'user': UserSerializer(profile).data,
            'total_cases': total,
            'closed_cases': closed,
            'active_cases': active,
            'won_cases': won,
            'win_percentage': win_percentage,
            'recent_cases': [
                {
                    'id': str(case.id),
                    'case_number': case.case_number,
                    'title': case.title,
                    'status': case.status,
                    'next_hearing_date': case.next_hearing_date,
                }
                for case in recent_cases
            ],
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def login_history(self, request, pk=None):
        """Get user login history"""
        user = self.get_object()
        
        # Only users can view their own history, admins can view all
        if request.user != user and request.user.role != 'admin':
            return Response(
                {'error': 'You do not have permission to view this user\'s history'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        history = LoginHistory.objects.filter(user=user).order_by('-login_time')[:50]
        serializer = LoginHistorySerializer(history, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Admin CSV import wizard (spec §12, §64): parse → validate → preview →
# confirm → import → report. No unvalidated data is ever inserted.
# ---------------------------------------------------------------------------

class StaffCSVPreviewView(generics.GenericAPIView):
    """Preview staff CSV: returns validated rows + row-level errors."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admins can import staff CSV files')
        role = request.data.get('role')
        if role not in ('judge', 'lawyer'):
            return Response({'error': 'role must be judge or lawyer'}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
        from .csv_import import preview_staff_csv
        result = preview_staff_csv(file_obj, role)
        return Response({
            'role': role,
            'total_rows': result.total_rows,
            'valid_count': result.valid_count,
            'error_count': result.error_count,
            'errors': result.errors[:200],
            'preview': result.rows[:50],
        })


class StaffCSVImportConfirmView(generics.GenericAPIView):
    """Confirm + import validated staff rows (must pass the exact rows from preview)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admins can import staff CSV files')
        role = request.data.get('role')
        rows = request.data.get('rows')
        if role not in ('judge', 'lawyer') or not isinstance(rows, list) or not rows:
            return Response({'error': 'role and rows are required'}, status=status.HTTP_400_BAD_REQUEST)
        from .csv_import import import_staff_rows
        created, report = import_staff_rows(rows, role, request.user)
        from apps.audit.services import record_audit
        record_audit(user=request.user, action='CSV_IMPORT', model_name='User',
                     object_id='', changes={'role': role, 'created': created, 'total': len(report)},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                     request_id=getattr(request, 'request_id', ''))
        return Response({'created': created, 'updated': len(report) - created, 'report': report})


class CaseCSVPreviewView(generics.GenericAPIView):
    """Preview cases CSV."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admins can import cases CSV files')
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)
        from .csv_import import preview_case_csv
        result = preview_case_csv(file_obj)
        return Response({
            'total_rows': result.total_rows,
            'valid_count': result.valid_count,
            'error_count': result.error_count,
            'errors': result.errors[:200],
            'preview': result.rows[:50],
        })


class CaseCSVImportConfirmView(generics.GenericAPIView):
    """Confirm + import validated case rows."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admins can import cases CSV files')
        rows = request.data.get('rows')
        if not isinstance(rows, list) or not rows:
            return Response({'error': 'rows are required'}, status=status.HTTP_400_BAD_REQUEST)
        from .csv_import import import_case_rows
        created, report = import_case_rows(rows, request.user)
        from apps.audit.services import record_audit
        record_audit(user=request.user, action='CSV_IMPORT', model_name='Case',
                     object_id='', changes={'created': created, 'total': len(report)},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                     request_id=getattr(request, 'request_id', ''))
        return Response({'created': created, 'report': report})


class CSVErrorReportView(generics.GenericAPIView):
    """
    Return the row-level validation errors from a CSV as a downloadable CSV
    report (spec §12: 'Optionally provide downloadable error report').
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            raise PermissionDenied('Only admins can generate CSV error reports')
        import_type = request.data.get('type', 'staff')
        role = request.data.get('role', 'judge')
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)

        from .csv_import import preview_staff_csv, preview_case_csv
        result = preview_staff_csv(file_obj, role) if import_type == 'staff' else preview_case_csv(file_obj)

        # Build CSV
        import csv as _csv
        import io as _io
        buf = _io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(['row', 'field', 'message'])
        for err in result.errors:
            writer.writerow([err.get('row', ''), err.get('field', ''), err.get('message', '')])

        from django.http import HttpResponse
        resp = HttpResponse(buf.getvalue(), content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="csv_import_errors_{import_type}.csv"'
        return resp


class TwoFactorStatusView(generics.GenericAPIView):
    """
    MFA status for the current user (spec §46).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .mfa import is_mfa_available, is_mfa_enabled, get_or_create_two_factor
        user = request.user
        tf = get_or_create_two_factor(user)
        return Response({
            'mfa_available': is_mfa_available(),
            'mfa_enabled': is_mfa_enabled(user),
            'provider': tf.provider,
            'providers_supported': ['totp', 'webauthn', 'sms', 'email'],
            'note': 'TOTP flow is implemented (enroll/verify/challenge). Set MFA_ENABLED=True in .env to activate.',
        })


class TwoFactorEnrollView(generics.GenericAPIView):
    """
    Begin TOTP enrollment: generate a secret + provisioning URI + QR image.
    The secret is stored (encrypted at rest) but 2FA is NOT enabled until
    the user verifies a code (see TwoFactorVerifyView).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.conf import settings
        if not getattr(settings, 'MFA_ENABLED', False):
            return Response({'error': 'MFA is not enabled on this instance'}, status=status.HTTP_400_BAD_REQUEST)
        from .mfa import generate_secret, provisioning_uri, qr_png_data_uri, get_or_create_two_factor
        user = request.user
        tf = get_or_create_two_factor(user)
        if tf.is_enabled:
            return Response({'error': '2FA is already enabled'}, status=status.HTTP_400_BAD_REQUEST)
        from .mfa import encrypt_secret
        secret = generate_secret()
        tf.provider = 'totp'
        tf.secret_encrypted = encrypt_secret(secret)
        tf.save()
        uri = provisioning_uri(user, secret)
        return Response({
            'secret': secret,
            'otpauth_url': uri,
            'qr_png': qr_png_data_uri(uri),
            'issuer': 'JCM',
            'account': user.email or user.username,
        })


class TwoFactorVerifyView(generics.GenericAPIView):
    """Verify a TOTP code and enable 2FA for the user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .mfa import verify_code, get_or_create_two_factor, decrypt_secret
        code = request.data.get('code', '')
        user = request.user
        tf = get_or_create_two_factor(user)
        if not tf.secret_encrypted:
            return Response({'error': 'No pending enrollment; call enroll first'}, status=status.HTTP_400_BAD_REQUEST)
        secret = decrypt_secret(tf.secret_encrypted)
        if not secret or not verify_code(secret, code):
            return Response({'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)
        tf.is_enabled = True
        tf.verified_at = timezone.now()
        tf.save()
        # Issue one-time recovery codes (plaintext shown only once — save them!)
        from .mfa import generate_recovery_codes
        recovery_codes = generate_recovery_codes(user)
        from apps.audit.services import record_audit
        record_audit(user=user, action='PERMISSION_CHANGED', model_name='TwoFactorAuth',
                     object_id=tf.id, changes={'action': 'mfa_enabled'},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response({
            'mfa_enabled': True,
            'message': 'Two-factor authentication enabled. Save your recovery codes now (shown once).',
            'recovery_codes': recovery_codes,
        })


class TwoFactorDisableView(generics.GenericAPIView):
    """Disable 2FA after verifying the current TOTP code."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .mfa import verify_code, get_or_create_two_factor, decrypt_secret
        code = request.data.get('code', '')
        user = request.user
        tf = get_or_create_two_factor(user)
        if not tf.is_enabled:
            return Response({'error': '2FA is not enabled'}, status=status.HTTP_400_BAD_REQUEST)
        secret = decrypt_secret(tf.secret_encrypted)
        if not secret or not verify_code(secret, code):
            return Response({'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)
        tf.is_enabled = False
        tf.secret_encrypted = ''
        tf.verified_at = None
        tf.save()
        from apps.audit.services import record_audit
        record_audit(user=user, action='PERMISSION_CHANGED', model_name='TwoFactorAuth',
                     object_id=tf.id, changes={'action': 'mfa_disabled'},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response({'mfa_enabled': False, 'message': 'Two-factor authentication disabled'})


class TwoFactorChallengeView(generics.GenericAPIView):
    """
    Exchange a challenge token + TOTP code for full JWT access (spec §46).
    Called after login returned mfa_required=True.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .mfa import verify_code, resolve_mfa_challenge, is_mfa_enabled, decrypt_secret, consume_recovery_code
        token = request.data.get('mfa_token', '')
        code = request.data.get('code', '')
        user = resolve_mfa_challenge(token)
        if not user:
            return Response({'error': 'Challenge expired or invalid. Please log in again.'}, status=status.HTTP_400_BAD_REQUEST)
        tf = getattr(user, 'two_factor', None)
        if not tf or not is_mfa_enabled(user):
            return Response({'error': '2FA is not enabled for this account'}, status=status.HTTP_400_BAD_REQUEST)
        secret = decrypt_secret(tf.secret_encrypted)
        totp_ok = bool(secret) and verify_code(secret, code)
        recovery_ok = (not totp_ok) and consume_recovery_code(user, code)
        if not totp_ok and not recovery_ok:
            return Response({'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class TwoFactorRecoveryCodesView(generics.GenericAPIView):
    """List remaining recovery codes (masked) for the current user (spec §46)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .mfa import is_mfa_enabled, list_recovery_codes
        if not is_mfa_enabled(request.user):
            return Response({'error': '2FA is not enabled'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'recovery_codes': list_recovery_codes(request.user)})


class TwoFactorRecoveryRegenerateView(generics.GenericAPIView):
    """Regenerate recovery codes (invalidates previous unused ones)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .mfa import is_mfa_enabled, generate_recovery_codes
        if not is_mfa_enabled(request.user):
            return Response({'error': '2FA is not enabled'}, status=status.HTTP_400_BAD_REQUEST)
        codes = generate_recovery_codes(request.user)
        from apps.audit.services import record_audit
        record_audit(user=request.user, action='PERMISSION_CHANGED', model_name='TwoFactorAuth',
                     object_id='', changes={'action': 'recovery_codes_regenerated'},
                     ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'))
        return Response({'recovery_codes': codes, 'message': 'Old codes invalidated. Save these new ones.'})


class TwoFactorWebAuthnView(generics.GenericAPIView):
    """
    WebAuthn/passkey provider interface (spec §46).
    The data model (TwoFactorWebAuthnCredential) is ready; wiring the full
    attestation flow requires a WebAuthn server (py_webauthn) + browser
    navigator.credentials. This endpoint reports status gracefully so the
    UI never breaks.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .mfa import get_or_create_two_factor
        tf = get_or_create_two_factor(request.user)
        creds = tf.webauthn_credentials.all()
        return Response({
            'provider_available': False,
            'note': 'WebAuthn provider not wired. Add py_webauthn + browser integration to enable passkeys.',
            'registered_credentials': [
                {'id': str(c.id), 'label': c.label, 'sign_count': c.sign_count,
                 'created_at': c.created_at.isoformat() if c.created_at else None}
                for c in creds
            ],
        })

    def post(self, request):
        return Response({
            'provider_available': False,
            'note': 'WebAuthn provider not wired. Add py_webauthn + browser integration to enable passkeys.',
        }, status=status.HTTP_400_BAD_REQUEST)
