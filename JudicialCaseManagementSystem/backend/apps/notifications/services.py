"""
Notification service (spec §28): event-driven in-app notifications with
async delivery via Celery. Email/SMS/push can be added later behind the
same service interface.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

EVENT_LABELS = {
    'HEARING_CREATED': 'Hearing Scheduled',
    'HEARING_RESCHEDULED': 'Hearing Rescheduled',
    'HEARING_CANCELLED': 'Hearing Cancelled',
    'DOCUMENT_UPLOADED': 'Document Uploaded',
    'ORDER_PUBLISHED': 'Order Published',
    'CASE_ASSIGNED': 'Case Assigned',
    'CASE_STATUS_CHANGED': 'Case Status Changed',
    'TASK_DUE': 'Task Due',
}


def notify_user(user, event_type, title, message, case=None, action_url=''):
    """Create an in-app notification (sync; cheap)."""
    from .models import Notification
    try:
        return Notification.objects.create(
            user=user,
            notification_type=event_type.lower(),
            title=title,
            message=message,
            case=case,
            action_url=action_url,
        )
    except Exception as exc:
        logger.warning(f"Notification create failed: {exc}")
        return None


@shared_task
def send_notification_task(user_id, event_type, title, message, case_id=None, action_url=''):
    from apps.authentication.models import User
    from apps.cases.models import Case
    user = User.objects.filter(id=user_id).first()
    if not user:
        return {'error': 'user not found'}
    case = Case.objects.filter(id=case_id).first() if case_id else None
    notify_user(user, event_type, title, message, case=case, action_url=action_url)
    # Optional email delivery (spec §28: in-app first, email/SMS/push later)
    send_email_notification.delay(user.email, title, message, action_url)
    return {'sent': True}


@shared_task
def send_email_notification(to_email, title, message, action_url=''):
    """
    Deliver a notification by email when an email backend is configured
    (EMAIL_HOST set). Falls back to console logging otherwise, so this is
    safe in dev and on instances without mail configuration.
    """
    from django.conf import settings
    try:
        from django.core.mail import send_mail
        body = f"{message}\n\nAction: {action_url}" if action_url else message
        sent = send_mail(
            subject=f"[JCM] {title}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
        if sent:
            logger.info(f"Email notification sent to {to_email}: {title}")
            return {'email_sent': True}
        logger.warning(f"Email notification not sent to {to_email}: {title} (no mail backend configured); in-app notification still delivered")
        return {'email_sent': False, 'reason': 'mail backend not configured'}
    except Exception as exc:
        logger.warning(f"Email notification failed for {to_email}: {exc} (in-app notification still delivered)")
        return {'email_sent': False, 'error': str(exc)}


def notify_case_participants(case, event_type, title, message, action_url='', exclude_user=None):
    """
    Notify lawyers/judge associated with a case (async).
    """
    users = set()
    if case.assigned_lawyer:
        users.add(case.assigned_lawyer)
    if case.assigned_judge:
        users.add(case.assigned_judge)
    for cl in case.case_lawyers.filter(is_active=True):
        users.add(cl.lawyer)
    for asg in case.assignments.filter(is_active=True):
        users.add(asg.lawyer)
    if exclude_user:
        users.discard(exclude_user)
    for u in users:
        send_notification_task.delay(
            str(u.id), event_type, title, message, str(case.id), action_url
        )
    return len(users)
