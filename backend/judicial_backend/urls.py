"""
URL configuration for judicial_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

api_patterns = [
    path('auth/', include('apps.authentication.urls')),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('cases/', include('apps.cases.urls')),
    path('courts/', include('apps.courts.urls')),
    path('hearings/', include('apps.hearings.urls')),
    path('orders/', include('apps.orders.urls')),
    path('documents/', include('apps.documents.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('ai/', include('apps.ai_assistant.urls')),
    path('audit/', include('apps.audit.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('public/', include('apps.cases.public_urls')),
    path('search/', include('apps.cases.search_urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),
    # Versioned alias (spec §48: clean REST APIs with versioning)
    path('api/v1/', include(api_patterns)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
