"""
Configuration API URLs powered by DRF router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BankingDetailViewSet, ChoiceViewSet, LocationViewSet, PostalInfoViewSet, RouteViewSet

router = DefaultRouter()
router.register(r"choices", ChoiceViewSet, basename="cfg-choice")
router.register(r"locations", LocationViewSet, basename="cfg-location")
router.register(r"routes", RouteViewSet, basename="cfg-route")
router.register(r"banking-details", BankingDetailViewSet, basename="cfg-banking-detail")
router.register(r"postal-info", PostalInfoViewSet, basename="cfg-postal-info")

urlpatterns = [
    path("", include(router.urls)),
]
