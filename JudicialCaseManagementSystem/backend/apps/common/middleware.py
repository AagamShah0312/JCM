"""
Middleware: request IDs and audit logging (spec §45, §58).
"""
import logging
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """Attach a request ID to every request for traceability."""

    def process_request(self, request):
        request.request_id = request.META.get('HTTP_X_REQUEST_ID') or uuid.uuid4().hex[:16]
        return None

    def process_response(self, request, response):
        request_id = getattr(request, 'request_id', '')
        if request_id:
            response['X-Request-ID'] = request_id
        return response


class AuditMiddleware(MiddlewareMixin):
    """
    Automatically log sensitive operations (spec §45).
    Views that perform a sensitive action can call
    `apps.audit.services.record_audit(...)` explicitly; this middleware
    provides a catch-all for login/logout and non-GET mutations on known
    sensitive models.
    """

    SENSITIVE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    SENSITIVE_PATH_PREFIXES = (
        '/api/cases/', '/api/hearings/', '/api/orders/', '/api/documents/',
        '/api/tasks/', '/api/auth/users/',
    )

    def process_response(self, request, response):
        if request.method not in self.SENSITIVE_METHODS:
            return response
        if not request.path.startswith(self.SENSITIVE_PATH_PREFIXES):
            return response
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return response

        from apps.audit.services import record_audit
        try:
            action = self._action_for(request)
            if action:
                record_audit(
                    user=request.user,
                    action=action,
                    model_name=self._model_for_path(request.path),
                    object_id=request.resolver_match.kwargs.get('pk') or '',
                    changes={},
                    ip_address=self._client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    request_id=getattr(request, 'request_id', ''),
                    status_code=response.status_code,
                )
        except Exception:
            logger.warning("Audit middleware could not record event", exc_info=True)
        return response

    @staticmethod
    def _client_ip(request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    @staticmethod
    def _action_for(request):
        method = request.method
        path = request.path
        if 'login' in path:
            return 'LOGIN'
        if 'logout' in path:
            return 'LOGOUT'
        if '/documents/' in path:
            return {
                'POST': 'DOCUMENT_UPLOADED',
                'DELETE': 'DOCUMENT_DELETED',
            }.get(method)
        if '/orders/' in path:
            return {'POST': 'ORDER_CREATED', 'PATCH': 'ORDER_UPDATED', 'PUT': 'ORDER_UPDATED'}.get(method)
        if '/hearings/' in path:
            return {'POST': 'HEARING_CREATED', 'PATCH': 'HEARING_UPDATED', 'PUT': 'HEARING_UPDATED'}.get(method)
        if '/cases/' in path:
            return {
                'POST': 'CASE_CREATED',
                'PATCH': 'CASE_UPDATED',
                'PUT': 'CASE_UPDATED',
                'DELETE': 'CASE_DELETED',
            }.get(method)
        if '/tasks/' in path:
            return {'POST': 'TASK_CREATED', 'PATCH': 'TASK_UPDATED'}.get(method)
        return 'OTHER'

    @staticmethod
    def _model_for_path(path):
        for part in ('cases', 'documents', 'orders', 'hearings', 'tasks', 'users'):
            if f'/{part}/' in path:
                return part.capitalize()
        return 'Unknown'
