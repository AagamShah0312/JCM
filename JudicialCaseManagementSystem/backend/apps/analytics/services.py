"""
Analytics services (spec §42, §43): case stats, distributions, adjournments,
cause list, calendar, case health, what-changed, smart scheduling.
"""
from datetime import timedelta

from django.db.models import Count, Q, Avg
from django.utils import timezone


def admin_case_stats():
    from apps.cases.models import Case
    total = Case.objects.filter(is_archived=False).count()
    return {
        'total_cases': total,
        'filed': Case.objects.filter(status='FILED', is_archived=False).count(),
        'registered': Case.objects.filter(status='REGISTERED', is_archived=False).count(),
        'pending': Case.objects.filter(status__in=['PENDING', 'FILED', 'REGISTERED'], is_archived=False).count(),
        'active': Case.objects.filter(status='ACTIVE', is_archived=False).count(),
        'adjourned': Case.objects.filter(status='ADJOURNED', is_archived=False).count(),
        'reserved_for_order': Case.objects.filter(status='RESERVED_FOR_ORDER', is_archived=False).count(),
        'disposed': Case.objects.filter(status='DISPOSED', is_archived=False).count(),
        'transferred': Case.objects.filter(status='TRANSFERRED', is_archived=False).count(),
        'closed': Case.objects.filter(status='CLOSED', is_archived=False).count(),
        'upcoming_hearings': Case.objects.filter(
            next_hearing_date__gte=timezone.now().date(), is_archived=False
        ).count(),
    }


def cases_by_type():
    from apps.cases.models import Case
    return list(
        Case.objects.filter(is_archived=False)
        .values('case_type').annotate(count=Count('id')).order_by('-count')
    )


def cases_by_court():
    from apps.cases.models import Case
    return list(
        Case.objects.filter(is_archived=False, court__isnull=False)
        .values('court__name').annotate(count=Count('id')).order_by('-count')
    )


def cases_by_judge():
    from apps.cases.models import Case
    return list(
        Case.objects.filter(is_archived=False, assigned_judge__isnull=False)
        .values('assigned_judge__email').annotate(count=Count('id')).order_by('-count')
    )


def case_age_distribution(thresholds=None):
    """
    Age buckets: <1y, 1-3y, 3-5y, 5-10y, 10+y (spec §43).
    thresholds: list of year boundaries, configurable.
    """
    from apps.cases.models import Case
    thresholds = thresholds or [1, 3, 5, 10]
    today = timezone.now().date()
    buckets = {}
    labels = []
    prev = 0
    for t in thresholds:
        labels.append((prev, t))
        prev = t
    labels.append((prev, None))  # 10+ years

    for (lo, hi) in labels:
        key = f"{lo}-{hi}" if hi else f"{lo}+"
        if hi is None:
            qs = Case.objects.filter(
                filing_date__lte=today - timedelta(days=lo * 365), is_archived=False
            )
        else:
            qs = Case.objects.filter(
                filing_date__gt=today - timedelta(days=hi * 365),
                filing_date__lte=today - timedelta(days=lo * 365),
                is_archived=False,
            )
        buckets[key] = qs.count()
    return buckets


def hearing_stats():
    from apps.hearings.models import Hearing
    return {
        'total': Hearing.objects.count(),
        'scheduled': Hearing.objects.filter(status='SCHEDULED').count(),
        'completed': Hearing.objects.filter(status='COMPLETED').count(),
        'adjourned': Hearing.objects.filter(status='ADJOURNED').count(),
        'cancelled': Hearing.objects.filter(status='CANCELLED').count(),
        'upcoming': Hearing.objects.filter(date__gte=timezone.now().date(), status='SCHEDULED').count(),
    }


def adjournment_analytics():
    """Adjournments by reason (spec §41/§42)."""
    from apps.hearings.models import Hearing, AdjournmentReasonOption
    reasons = AdjournmentReasonOption.objects.filter(is_active=True)
    data = []
    for r in reasons:
        count = Hearing.objects.filter(adjournment_reason=r).count()
        if count:
            data.append({'code': r.code, 'label': r.label, 'count': count})
    data.sort(key=lambda x: -x['count'])
    return {
        'by_reason': data,
        'total_adjourned': Hearing.objects.filter(status='ADJOURNED').count(),
    }


def cases_requiring_attention(no_hearing_days=120, high_adjournment=3):
    """Admin flags: old cases, long gaps, high adjournments (spec §42)."""
    from apps.cases.models import Case
    today = timezone.now().date()
    old_threshold = today - timedelta(days=365 * 5)
    gap_threshold = today - timedelta(days=no_hearing_days)

    old_cases = Case.objects.filter(
        filing_date__lte=old_threshold, is_archived=False,
        status__in=['PENDING', 'ACTIVE', 'ADJOURNED'],
    ).count()

    long_gap = Case.objects.filter(
        is_archived=False, status__in=['PENDING', 'ACTIVE', 'ADJOURNED'],
    ).filter(
        Q(next_hearing_date__isnull=True) | Q(next_hearing_date__lt=gap_threshold)
    ).count()

    from apps.hearings.models import Hearing
    high_adj = []
    case_ids = (
        Hearing.objects.filter(status='ADJOURNED')
        .values('case_id').annotate(n=Count('id')).filter(n__gte=high_adjournment)
        .values_list('case_id', flat=True)
    )
    for cid in case_ids:
        case = Case.objects.filter(id=cid).first()
        if case:
            high_adj.append({'case_number': case.case_number, 'title': case.title,
                             'adjournments': Hearing.objects.filter(case=case, status='ADJOURNED').count()})

    return {
        'cases_older_than_5_years': old_cases,
        'cases_with_long_gap_since_hearing': long_gap,
        'cases_with_high_adjournment_count': high_adj,
    }


def case_health(case):
    """Case health indicators (spec §38) — administrative, not legal judgment."""
    from apps.hearings.models import Hearing
    today = timezone.now().date()
    hearings = Hearing.objects.filter(case=case)
    completed = hearings.filter(status='COMPLETED').count()
    adjourned = hearings.filter(status='ADJOURNED').count()
    last_hearing = hearings.order_by('-date').first()
    days_since_last_hearing = (today - last_hearing.date).days if last_hearing and last_hearing.date else None
    docs_count = case.documents.filter(state='ACTIVE').count()
    orders_count = case.orders.count()
    pending_processing = case.documents.filter(processing_state__in=['UPLOADED', 'PROCESSING', 'OCR_REQUIRED']).count()

    warnings = []
    if days_since_last_hearing is not None and days_since_last_hearing > 120:
        warnings.append({'code': 'NO_HEARING_EXTENDED', 'message': f'No hearing for {days_since_last_hearing} days'})
    if pending_processing:
        warnings.append({'code': 'PENDING_DOC_PROCESSING', 'message': f'{pending_processing} document(s) awaiting processing'})
    if adjourned >= 3:
        warnings.append({'code': 'HIGH_ADJOURNMENTS', 'message': f'{adjourned} adjournments'})
    if case.next_hearing_date and case.next_hearing_date < today:
        warnings.append({'code': 'OVERDUE_HEARING', 'message': 'Next hearing date is in the past'})

    return {
        'case_age_days': case.case_age_days,
        'hearings_total': hearings.count(),
        'hearings_completed': completed,
        'adjournments': adjourned,
        'days_since_last_hearing': days_since_last_hearing,
        'documents_count': docs_count,
        'orders_count': orders_count,
        'next_hearing_date': case.next_hearing_date.isoformat() if case.next_hearing_date else None,
        'warnings': warnings,
    }


def cause_list_for_user(user, date=None, courtroom_id=None):
    """Cause list for a judge/lawyer (spec §26)."""
    from apps.hearings.models import Hearing
    from apps.cases.permissions import case_queryset_for

    date = date or timezone.now().date()
    qs = Hearing.objects.filter(date=date).select_related('case', 'judge', 'courtroom', 'case__court')

    if user.role == 'judge':
        qs = qs.filter(Q(judge=user) | Q(case__assigned_judge=user) | Q(case__created_by=user))
    elif user.role == 'lawyer':
        case_ids = case_queryset_for(user).values_list('id', flat=True)
        qs = qs.filter(case_id__in=case_ids)
    elif user.role == 'guest':
        qs = qs.filter(is_public=True)
    # admin: all

    if courtroom_id:
        qs = qs.filter(courtroom_id=courtroom_id)

    return qs.order_by('start_time', 'courtroom__name')


def calendar_events_for_user(user, start, end):
    """Calendar events (hearings + tasks + deadlines) within a date range (spec §27)."""
    from apps.hearings.models import Hearing
    from apps.tasks.models import Task
    from apps.cases.permissions import case_queryset_for, task_queryset_for

    events = []

    # Hearings the user may see
    if user.role == 'admin':
        hearings = Hearing.objects.filter(date__range=[start, end])
    elif user.role == 'guest':
        hearings = Hearing.objects.filter(date__range=[start, end], is_public=True)
    else:
        case_ids = case_queryset_for(user).values_list('id', flat=True)
        hearings = Hearing.objects.filter(date__range=[start, end], case_id__in=case_ids)

    for h in hearings:
        events.append({
            'type': 'hearing',
            'id': str(h.id),
            'case_number': h.case.case_number,
            'title': f"Hearing #{h.hearing_number} — {h.case.case_number}",
            'date': h.date.isoformat(),
            'time': h.start_time.isoformat() if h.start_time else None,
            'status': h.status,
        })

    # Tasks
    tasks = task_queryset_for(user).filter(due_date__range=[start, end])
    for t in tasks:
        events.append({
            'type': 'task',
            'id': str(t.id),
            'title': t.title,
            'date': t.due_date.isoformat(),
            'status': t.status,
            'priority': t.priority,
        })

    return events


def what_changed(case, since=None, last_visit=None):
    """
    Changes in a case since the user's last visit (spec §39).
    Returns a list of human-readable change strings.
    """
    from apps.hearings.models import Hearing, HearingProceeding
    from apps.orders.models import Order
    from apps.cases.models import CaseEvent

    since = since or last_visit
    changes = []
    if not since:
        return changes

    events = CaseEvent.objects.filter(case=case, created_at__gt=since).order_by('created_at')
    for ev in events:
        changes.append(ev.title)

    orders_published = Order.objects.filter(case=case, published_at__gt=since)
    for o in orders_published:
        changes.append(f"New order published: {o.title}")

    hearings = Hearing.objects.filter(case=case, updated_at__gt=since)
    for h in hearings:
        changes.append(f"Hearing #{h.hearing_number} on {h.date} updated ({h.status})")

    proceedings = HearingProceeding.objects.filter(hearing__case=case, created_at__gt=since)
    for p in proceedings:
        changes.append(f"Proceedings recorded for Hearing #{p.hearing.hearing_number}")

    new_docs = case.documents.filter(uploaded_at__gt=since)
    for d in new_docs:
        changes.append(f"Document uploaded: {d.file_name}")

    if case.next_hearing_date:
        changes.append(f"Next hearing date: {case.next_hearing_date}")

    # dedupe, preserve order
    seen = set()
    out = []
    for c in changes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def smart_hearing_suggestions(user, case, preferred_date=None, days=14):
    """
    Scheduling assistance (spec §44): suggest dates with conflict counts.
    NEVER auto-schedules; the judge decides.
    """
    from apps.hearings.models import Hearing

    if not preferred_date:
        preferred_date = timezone.now().date() + timedelta(days=7)

    suggestions = []
    judge = case.assigned_judge
    for offset in range(0, days):
        d = preferred_date + timedelta(days=offset)
        if d.weekday() >= 5:  # skip weekends
            continue
        conflicts = 0
        # judge busy?
        if judge:
            conflicts += Hearing.objects.filter(
                judge=judge, date=d, status__in=['SCHEDULED', 'IN_PROGRESS']
            ).count()
        # courtroom busy?
        if case.courtroom_id:
            conflicts += Hearing.objects.filter(
                courtroom=case.courtroom, date=d, status__in=['SCHEDULED', 'IN_PROGRESS']
            ).count()
        suggestions.append({
            'date': d.isoformat(),
            'conflicts': conflicts,
            'recommended': conflicts == 0,
        })

    suggestions.sort(key=lambda x: (x['conflicts'], x['date']))
    return suggestions[:10]
