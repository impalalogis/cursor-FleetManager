"""
Entity API URLs powered by DRF router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DriverDocumentViewSet,
    DriverViewSet,
    OrganizationDocumentViewSet,
    OrganizationViewSet,
    VehicleDocumentViewSet,
    VehicleViewSet,
)

router = DefaultRouter()
router.register(r"organizations", OrganizationViewSet, basename="entity-organization")
router.register(r"organization-documents", OrganizationDocumentViewSet, basename="entity-organization-document")
router.register(r"drivers", DriverViewSet, basename="entity-driver")
router.register(r"driver-documents", DriverDocumentViewSet, basename="entity-driver-document")
router.register(r"vehicles", VehicleViewSet, basename="entity-vehicle")
router.register(r"vehicle-documents", VehicleDocumentViewSet, basename="entity-vehicle-document")

urlpatterns = [
    path("", include(router.urls)),
]
