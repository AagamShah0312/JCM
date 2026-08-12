"""
Global search across cases, parties, hearings, documents, orders (spec §30).
Authorization is applied per entity; only content the user may access is
returned. Guests see public-only results.
"""
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.cases.permissions import case_queryset_for, document_queryset_for, can_view_hearing
from apps.cases.serializers import GuestCaseSerializer, CaseListSerializer
from apps.documents.serializers import GuestDocumentSerializer, CaseDocumentSerializer


class GlobalSearchView(APIView):
    """Search across cases, hearings, documents and orders (authorized only)."""

    def get_permissions(self):
        # Guests may search public information; authenticated users search their scope.
        if self.request.user and self.request.user.is_authenticated:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response({'cases': [], 'documents': [], 'hearings': [], 'orders': []})

        user = request.user if request.user.is_authenticated else None
        results = {
            'cases': self._search_cases(user, q),
            'documents': self._search_documents(user, q),
            'hearings': self._search_hearings(user, q),
            'orders': self._search_orders(user, q),
        }
        return Response(results)

    def _search_cases(self, user, q):
        from apps.cases.models import Case
        qs = case_queryset_for(user).filter(
            Q(case_number__icontains=q) | Q(cnr_number__icontains=q) | Q(title__icontains=q)
            | Q(plaintiff_name__icontains=q) | Q(defendant_name__icontains=q)
            | Q(parties__name__icontains=q)
        ).distinct()[:10]
        if not user:
            return GuestCaseSerializer(qs, many=True).data
        return CaseListSerializer(qs, many=True, context={'request': self.request}).data

    def _search_documents(self, user, q):
        from apps.documents.models import CaseDocument
        qs = document_queryset_for(user).filter(
            Q(file_name__icontains=q) | Q(description__icontains=q)
        ).distinct()[:10]
        if not user:
            return GuestDocumentSerializer(qs, many=True).data
        return CaseDocumentSerializer(qs, many=True, context={'request': self.request}).data

    def _search_hearings(self, user, q):
        from apps.hearings.models import Hearing
        from apps.hearings.serializers import GuestHearingSerializer, HearingSerializer
        if user and user.is_authenticated:
            case_ids = list(case_queryset_for(user).values_list('id', flat=True))
            qs = Hearing.objects.filter(
                Q(case_id__in=case_ids)
                & (Q(purpose__icontains=q) | Q(case__case_number__icontains=q) | Q(case__title__icontains=q)),
            ).distinct()[:10]
            return HearingSerializer(qs, many=True, context={'request': self.request}).data
        qs = Hearing.objects.filter(
            Q(is_public=True)
            & (Q(purpose__icontains=q) | Q(case__case_number__icontains=q) | Q(case__title__icontains=q)),
        )[:10]
        return GuestHearingSerializer(qs, many=True).data

    def _search_orders(self, user, q):
        from apps.orders.models import Order
        from apps.orders.serializers import GuestOrderSerializer, OrderSerializer
        if user and user.is_authenticated:
            case_ids = list(case_queryset_for(user).values_list('id', flat=True))
            qs = Order.objects.filter(
                Q(case_id__in=case_ids)
                & (Q(title__icontains=q) | Q(case__case_number__icontains=q)),
            ).exclude(status='DRAFT')[:10]
            return OrderSerializer(qs, many=True, context={'request': self.request}).data
        qs = Order.objects.filter(
            Q(is_public=True)
            & Q(status='PUBLISHED')
            & (Q(title__icontains=q) | Q(case__case_number__icontains=q)),
        )[:10]
        return GuestOrderSerializer(qs, many=True).data
