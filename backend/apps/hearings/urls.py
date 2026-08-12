"""
URL routing for hearings app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HearingViewSet, AdjournmentReasonViewSet

router = DefaultRouter()
router.register(r'adjournment-reasons', AdjournmentReasonViewSet, basename='adjournment-reason')
router.register(r'', HearingViewSet, basename='hearing')

urlpatterns = [
    path('', include(router.urls)),
]
