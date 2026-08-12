"""
Guest/public API (spec §24, §25, §68).

Guests see ONLY explicitly public information:
- public cases (is_public=True)
- public hearings, public orders (published), public documents (PUBLIC)
- public timeline events

This intentionally uses separate, restricted serializers — never the
authenticated-user serializers.
"""
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from apps.cases.models import Case, CaseEvent
from apps.cases.serializers import GuestCaseSerializer
from apps.common.exceptions import NotFoundError
from apps.documents.models import CaseDocument
from apps.documents.serializers import GuestDocumentSerializer
from apps.hearings.models import Hearing
from apps.hearings.serializers import GuestHearingSerializer
from apps.orders.models import Order
from apps.orders.serializers import GuestOrderSerializer


class PublicCaseSearchView(APIView):
    """Public case search: case number, CNR, party name, type, court, date, status."""
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Case.objects.filter(is_public=True, is_archived=False)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(case_number__icontains=search)
                | Q(cnr_number__icontains=search)
                | Q(title__icontains=search)
                | Q(plaintiff_name__icontains=search)
                | Q(defendant_name__icontains=search)
                | Q(parties__name__icontains=search)
            ).distinct()

        case_type = request.query_params.get('case_type')
        if case_type:
            qs = qs.filter(case_type__iexact=case_type)

        court = request.query_params.get('court')
        if court:
            qs = qs.filter(Q(court__name__icontains=court) | Q(court_name__icontains=court))

        status_val = request.query_params.get('status')
        if status_val:
            qs = qs.filter(status=status_val.upper())

        filing_from = request.query_params.get('filing_from')
        if filing_from:
            qs = qs.filter(filing_date__gte=filing_from)

        filing_to = request.query_params.get('filing_to')
        if filing_to:
            qs = qs.filter(filing_date__lte=filing_to)

        qs = qs.order_by('-filing_date')[:100]
        serializer = GuestCaseSerializer(qs, many=True)
        return Response({'count': len(serializer.data), 'results': serializer.data})


class PublicCaseDetailView(APIView):
    """Public case detail + timeline (public events only)."""
    permission_classes = [AllowAny]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id, is_public=True, is_archived=False).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found or not public')

        events = case.events.filter(metadata__public=True)
        # plus any event types that are inherently public
        public_event_types = ['CASE_FILED', 'CASE_REGISTERED', 'ORDER_PUBLISHED', 'STATUS_CHANGED']
        events = case.events.filter(event_type__in=public_event_types).order_by('-event_date')[:50]

        return Response({
            'case': GuestCaseSerializer(case).data,
            'timeline': [
                {
                    'event_type': e.event_type,
                    'title': e.title,
                    'description': e.description,
                    'date': e.event_date.isoformat() if e.event_date else None,
                    'related_entity': e.related_entity,
                }
                for e in events
            ],
        })


class PublicCaseHearingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id, is_public=True, is_archived=False).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found or not public')
        hearings = Hearing.objects.filter(case=case, is_public=True).order_by('-date')
        return Response({'hearings': GuestHearingSerializer(hearings, many=True).data})


class PublicCaseOrdersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id, is_public=True, is_archived=False).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found or not public')
        orders = Order.objects.filter(case=case, is_public=True, status='PUBLISHED').order_by('-date')
        return Response({'orders': GuestOrderSerializer(orders, many=True).data})


class PublicCaseDocumentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id, is_public=True, is_archived=False).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found or not public')
        docs = CaseDocument.objects.filter(case=case, visibility='PUBLIC', state='ACTIVE').order_by('-uploaded_at')
        return Response({'documents': GuestDocumentSerializer(docs, many=True).data})


class PublicCaseNextHearingView(APIView):
    """Public next-hearing info (spec §24)."""
    permission_classes = [AllowAny]

    def get(self, request, case_id):
        case = Case.objects.filter(id=case_id, is_public=True, is_archived=False).first()
        if not case:
            raise NotFoundError('CASE_NOT_FOUND', 'Case not found or not public')
        next_h = Hearing.objects.filter(case=case, is_public=True, date__gte=__import__('django.utils.timezone', fromlist=['now']).now().date(), status='SCHEDULED').order_by('date').first()
        return Response({
            'case_number': case.case_number,
            'next_hearing_date': case.next_hearing_date.isoformat() if case.next_hearing_date else None,
            'next_hearing': GuestHearingSerializer(next_h).data if next_h else None,
        })
