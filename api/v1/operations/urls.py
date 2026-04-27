"""
Operations API URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConsignmentDetail, ConsignmentListCreate, ConsignmentGroupListCreate,
    ConsignmentGroupDetail, ShipmentListCreate, ShipmentDetail, ShipmentExpenseListCreate, ShipmentExpenseDetail,
    ShipmentStatusListCreate, ShipmentStatusDetail, DriverAdvanceListCreate, DriverAdvanceDetail, DriverAdvanceSettle,
    DriverAdvanceSummary
)
urlpatterns = [

    path("consignments/", ConsignmentListCreate.as_view(), name="consignment-list-create"),
    path("consignments/<int:pk>/", ConsignmentDetail.as_view(), name="consignment-detail"),
    path("consignment-groups/", ConsignmentGroupListCreate.as_view(), name="consignment-group-list-create"),
    path("consignment-groups/<int:pk>/", ConsignmentGroupDetail.as_view(), name="consignment-group-detail"),
    path("shipments/", ShipmentListCreate.as_view(), name="shipment-list-create"),
    path("shipments/<int:pk>/", ShipmentDetail.as_view(), name="shipment-detail"),
    path("shipment-expenses/", ShipmentExpenseListCreate.as_view(), name="shipment-expense-list-create"),
    path("shipment-expenses/<int:pk>/", ShipmentExpenseDetail.as_view(), name="shipment-expense-detail"),
    path("shipment-status/", ShipmentStatusListCreate.as_view(), name="shipment-status-list-create"),
    path("shipment-status/<int:pk>/", ShipmentStatusDetail.as_view(), name="shipment-status-detail"),
    path("driver-advances/", DriverAdvanceListCreate.as_view(), name="driver-advance-list-create"),
    path("driver-advances/<int:pk>/", DriverAdvanceDetail.as_view(), name="driver-advance-detail"),
    path("driver-advances/<int:pk>/settle/", DriverAdvanceSettle.as_view(), name="driver-advance-settle"),
    path("driver-advances/summary/", DriverAdvanceSummary.as_view(), name="driver-advance-summary"),
]
