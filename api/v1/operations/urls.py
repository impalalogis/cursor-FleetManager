"""
Operations API URLs powered by DRF router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ConsignmentGroupViewSet,
    ConsignmentViewSet,
    DieselViewSet,
    DriverAdvanceViewSet,
    ShipmentExpenseViewSet,
    ShipmentStatusViewSet,
    ShipmentViewSet,
)

router = DefaultRouter()
router.register(r"consignments", ConsignmentViewSet, basename="ops-consignment")
router.register(r"consignment-groups", ConsignmentGroupViewSet, basename="ops-consignment-group")
router.register(r"shipments", ShipmentViewSet, basename="ops-shipment")
router.register(r"shipment-expenses", ShipmentExpenseViewSet, basename="ops-shipment-expense")
router.register(r"shipment-status", ShipmentStatusViewSet, basename="ops-shipment-status")
router.register(r"driver-advances", DriverAdvanceViewSet, basename="ops-driver-advance")
router.register(r"diesel", DieselViewSet, basename="ops-diesel")

urlpatterns = [
    path("", include(router.urls)),
]
