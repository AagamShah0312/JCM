"""
Global search URL (spec §30). Included at /api/search/ and /api/v1/search/.
"""
from django.urls import path
from .global_search import GlobalSearchView

urlpatterns = [
    path('', GlobalSearchView.as_view(), name='global-search'),
]
