"""
Audit service: helper for recording append-only audit events (spec §45).
"""
from django.utils import timezone

from .models import AuditLog


def record_audit(*, user=None, action, model_name, object_id='', changes=None,
                 ip_address='0.0.0.0', user_agent='', request_id='', metadata=None,
                 status_code=None):
    """Create an audit record. Returns the AuditLog instance."""
    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        changes=changes or {},
        ip_address=ip_address or '0.0.0.0',
        user_agent=user_agent or '',
        request_id=request_id or '',
        metadata=metadata or {},
        status_code=status_code,
    )


def audit_case_event(*, user, case, action, changes=None, request=None, extra=None):
    """Convenience for case-scoped audit events."""
    return record_audit(
        user=user,
        action=action,
        model_name='Case',
        object_id=str(case.id) if case else '',
        changes=changes or {},
        ip_address=request.META.get('HTTP_X_FORWARDED_FOR', '0.0.0.0').split(',')[0].strip() if request else '0.0.0.0',
        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
        request_id=getattr(request, 'request_id', '') if request else '',
        metadata=extra or {},
    )
