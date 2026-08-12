"""
URL configuration for judicial_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/cases/', include('apps.cases.urls')),
    path('api/courts/', include('apps.courts.urls')),
    path('api/hearings/', include('apps.hearings.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/documents/', include('apps.documents.urls')),
    path('api/tasks/', include('apps.tasks.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/ai/', include('apps.ai_assistant.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/public/', include('apps.cases.public_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
