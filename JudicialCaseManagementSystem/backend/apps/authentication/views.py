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
    MFA status for the current user (spec §46, MFA-ready architecture).
    Returns whether 2FA is available/enabled and the supported providers.
    The verification flow itself is intentionally not implemented until a
    provider (TOTP/WebAuthn) is configured.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        user = request.user
        two_factor = getattr(user, 'two_factor', None)
        return Response({
            'mfa_available': bool(getattr(settings, 'MFA_ENABLED', False)),
            'mfa_enabled': bool(two_factor and two_factor.is_enabled),
            'provider': two_factor.provider if two_factor else None,
            'providers_supported': ['totp', 'webauthn', 'sms', 'email'],
            'note': 'MFA provider not configured. Set MFA_ENABLED=True and add a TOTP/WebAuthn provider to enable enrollment.',
        })
