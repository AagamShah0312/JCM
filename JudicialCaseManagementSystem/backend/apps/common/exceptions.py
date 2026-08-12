"""
Centralized error handling (spec §54, §58).

All API errors use a consistent structure:
    {
      "success": false,
      "error": {
        "code": "CASE_NOT_FOUND",
        "message": "The requested case could not be found."
      }
    }
Internal exceptions are logged with details but never leaked to users.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Application-level error with a stable code and HTTP status."""

    def __init__(self, code, message, http_status=400, details=None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)


class NotFoundError(APIError):
    def __init__(self, code='NOT_FOUND', message='Resource not found', details=None):
        super().__init__(code, message, 404, details)


class PermissionDeniedError(APIError):
    def __init__(self, code='PERMISSION_DENIED', message='You do not have permission to perform this action', details=None):
        super().__init__(code, message, 403, details)


class ValidationError_(APIError):
    def __init__(self, code='VALIDATION_ERROR', message='Validation failed', details=None):
        super().__init__(code, message, 400, details)


def _error_response(code, message, details=None, http_status=400):
    body = {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        },
    }
    if details:
        body['error']['details'] = details
    return Response(body, status=http_status)


def jcm_exception_handler(exc, context):
    """
    DRF exception handler wrapper. Maps known exceptions to the standard
    error envelope and logs detailed errors internally.
    """
    request = getattr(context, 'request', None)

    # Application-level API errors
    if isinstance(exc, APIError):
        if exc.http_status >= 500:
            logger.error(
                f"APIError {exc.code}: {exc.message}",
                exc_info=exc,
                extra={'request_id': getattr(request, 'request_id', '')},
            )
        return _error_response(exc.code, exc.message, exc.details, exc.http_status)

    # DRF's built-in handling (validation errors, auth failures, not found, etc.)
    response = exception_handler(exc, context)

    if response is not None:
        # Normalize DRF errors into the standard envelope
        detail = response.data
        code = 'VALIDATION_ERROR'
        message = 'Validation failed'
        details = detail

        if isinstance(detail, dict):
            # Common DRF codes
            if 'detail' in detail and isinstance(detail['detail'], str):
                d = detail['detail']
                code_map = {
                    'Authentication credentials were not provided.': ('AUTH_REQUIRED', 401),
                    'Invalid token.': ('INVALID_TOKEN', 401),
                    'Token is invalid or expired': ('INVALID_TOKEN', 401),
                    'Not found.': ('NOT_FOUND', 404),
                    'You do not have permission to perform this action.': ('PERMISSION_DENIED', 403),
                }
                if d in code_map:
                    code, default_status = code_map[d]
                else:
                    code = 'REQUEST_ERROR'
                message = d
                details = {}
            elif 'non_field_errors' in detail:
                message = '; '.join(detail['non_field_errors']) if isinstance(detail['non_field_errors'], list) else str(detail['non_field_errors'])
                code = 'VALIDATION_ERROR'
            else:
                # field-level errors
                field_msgs = []
                for field, errs in detail.items():
                    if isinstance(errs, list):
                        field_msgs.append(f"{field}: {errs[0] if errs else ''}")
                    else:
                        field_msgs.append(f"{field}: {errs}")
                message = '; '.join(field_msgs)[:500]
                details = detail

        http_status = response.status_code
        return _error_response(code, message, details, http_status)

    # Unhandled exceptions: log, return generic 500 (never leak stack traces)
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=exc,
        extra={'request_id': getattr(request, 'request_id', '') if request else ''},
    )
    return _error_response('INTERNAL_ERROR', 'An unexpected error occurred. Please try again later.', None, 500)
