"""
Celery tasks for notifications (spec §28): scheduled notification delivery
and the beat schedule entry that triggers it.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_notifications():
    """
    Send scheduled notifications whose scheduled_date/time has passed
    (spec §28: 'Use Celery for asynchronous notification delivery').
    """
    from .models import NotificationSchedule
    from .services import send_notification_task
    now = timezone.now()
    due = NotificationSchedule.objects.filter(
        is_sent=False,
        scheduled_date__lte=now.date(),
    ).select_related('case')
    sent = 0
    for sched in due:
        scheduled_at = timezone.make_aware(
            timezone.datetime.combine(sched.scheduled_date, sched.scheduled_time or timezone.datetime.min.time())
        ) if sched.scheduled_time else None
        if scheduled_at and scheduled_at > now:
            continue
        for recipient in sched.recipients.all():
            send_notification_task.delay(
                str(recipient.id),
                sched.notification_type,
                sched.notification_type.replace('_', ' ').title(),
                sched.message,
                str(sched.case_id) if sched.case_id else None,
            )
        sched.is_sent = True
        sched.sent_at = now
        sched.save(update_fields=['is_sent', 'sent_at'])
        sent += 1
    if sent:
        logger.info(f"process_scheduled_notifications: delivered {sent} scheduled notification(s)")
    return {'delivered': sent}
