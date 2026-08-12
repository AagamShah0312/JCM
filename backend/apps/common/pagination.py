"""Server-side pagination with a client-overridable page size (spec §52)."""
from rest_framework.pagination import PageNumberPagination


class JCMPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
