"""
Public (guest) endpoints — no auth required (spec §24-§25).
"""
from django.urls import path
from .public_views import (
    PublicCaseSearchView, PublicCaseDetailView, PublicCaseHearingsView,
    PublicCaseOrdersView, PublicCaseDocumentsView, PublicCaseNextHearingView,
)

urlpatterns = [
    path('cases/', PublicCaseSearchView.as_view(), name='public-case-search'),
    path('cases/<uuid:case_id>/', PublicCaseDetailView.as_view(), name='public-case-detail'),
    path('cases/<uuid:case_id>/hearings/', PublicCaseHearingsView.as_view(), name='public-case-hearings'),
    path('cases/<uuid:case_id>/orders/', PublicCaseOrdersView.as_view(), name='public-case-orders'),
    path('cases/<uuid:case_id>/documents/', PublicCaseDocumentsView.as_view(), name='public-case-documents'),
    path('cases/<uuid:case_id>/next-hearing/', PublicCaseNextHearingView.as_view(), name='public-case-next-hearing'),
]
