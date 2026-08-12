"""
Views for analytics app: admin analytics, cause list, calendar, case health,
what-changed, smart scheduling (spec §26-§27, §38-§44).
"""
from datetime import timedelta

from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.cases.models import Case
from apps.cases.permissions import can_view_case
from apps.common.exceptions import PermissionDeniedError, NotFoundError, ValidationError_
from .services import (
    admin_case_stats, cases_by_type, cases_by_court, cases_by_judge,
    case_age_distribution, hearing_stats, adjournment_analytics,
    cases_requiring_attention, case_health, cause_list_for_user,
    calendar_events_for_user, what_changed, smart_hearing_suggestions,
)


class AdminAnalyticsView(APIView):
    """Admin analytics dashboard data (spec §42/§43)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            raise PermissionDeniedError('PERMISSION_DENIED', 'Only admins can view system analytics')
        return Response({
            'case_stats': admin_case_stats(),
            'cases_by_type': cases_by_type(),
            'cases_by_court': cases_by_court(),
            'cases_by_judge': cases_by_judge(),
            'case_age_distribution': case_age_distribution(),
            'hearing_stats': hearing_stats(),
            'adjournment_analytics': adjournment_analytics(),
            'attention': cases_requiring_attention(),
        })


class CauseListView(APIView):
    """Cause list for the day (spec §26)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date = request.query_params.get('date') or timezone.now().date().isoformat()
        courtroom_id = request.query_params.get('courtroom')
        from apps.hearings.serializers import HearingSerializer
        qs = cause_list_for_user(request.user, date=date, courtroom_id=courtroom_id)
        return Response({
            'date': date,
            'count': qs.count(),
            'hearings': HearingSerializer(qs, many=True, context={'request': request}).data,
        })


class CalendarEventsView(APIView):
    """Calendar events for a date range (spec §27)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if not start or not end:
            raise ValidationError_('VALIDATION_ERROR', 'start and end (YYYY-MM-DD) are required')
        try:
            start_d = timezone.datetime.fromisoformat(start).date()
            end_d = timezone.datetime.fromisoformat(end).date()
        except ValueError:
            raise ValidationError_('VALIDATION_ERROR', 'Invalid date format')
        events = calendar_events_for_user(request.user, start_d, end_d)
        return Response({'events': events})


class CaseHealthView(APIView):
    """Case health indicators (spec §38)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found')
        if not can_view_case(request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Not authorized to this case')
        return Response(case_health(case))


class WhatChangedView(APIView):
    """What changed in a case since last visit (spec §39)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found')
        if not can_view_case(request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Not authorized to this case')

        since = request.query_params.get('since')
        if since:
            from datetime import datetime
            try:
                since_dt = datetime.fromisoformat(since)
            except ValueError:
                raise ValidationError_('VALIDATION_ERROR', 'Invalid since datetime')
        else:
            # fall back to the user's last AI visit (store in session-like key)
            since_dt = None
            last_visit = request.session.get(f'case_visit_{case.id}')
            if last_visit:
                from datetime import datetime
                since_dt = datetime.fromisoformat(last_visit)

        # Record this visit
        request.session[f'case_visit_{case.id}'] = timezone.now().isoformat()

        changes = what_changed(case, since=since_dt)

        # AI summary (optional)
        ai_summary = ''
        try:
            from apps.ai.services import what_changed_summary
            result = what_changed_summary(request.user, case, changes)
            ai_summary = result.get('summary', '')
        except Exception:
            pass

        return Response({'changes': changes, 'ai_summary': ai_summary})


class SmartSchedulingView(APIView):
    """Hearing date suggestions with conflict counts (spec §44)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found')
        if not can_view_case(request.user, case):
            raise PermissionDeniedError('PERMISSION_DENIED', 'Not authorized to this case')
        preferred = request.query_params.get('preferred_date')
        suggestions = smart_hearing_suggestions(request.user, case, preferred_date=preferred)
        return Response({
            'suggestions': suggestions,
            'note': 'Suggestions only. The judge makes the final decision.',
        })
