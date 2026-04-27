"""
Operations API URLs
"""

from django.urls import path

from .views import (
    ConsignmentDetail,
    ConsignmentGroupDetail,
    ConsignmentGroupListCreate,
    ConsignmentGroupRecalculateTotals,
    ConsignmentListCreate,
    ConsignmentRecalculateFreight,
    DieselDetail,
    DieselListCreate,
    DieselSummary,
    DriverAdvanceDetail,
    DriverAdvanceListCreate,
    DriverAdvanceSettle,
    DriverAdvanceSummary,
    DriverLedgerExcelView,
    DriverLedgerView,
    ShipmentCalculateDistance,
    ShipmentCalculateTotals,
    ShipmentDetail,
    ShipmentExpenseByAutocomplete,
    ShipmentExpenseDetail,
    ShipmentExpenseListCreate,
    ShipmentLRPdfView,
    ShipmentListCreate,
    ShipmentNextLRPreview,
    ShipmentStatusDetail,
    ShipmentStatusListCreate,
)

urlpatterns = [

    path("consignments/", ConsignmentListCreate.as_view(), name="consignment-list-create"),
    path("consignments/<int:pk>/", ConsignmentDetail.as_view(), name="consignment-detail"),
    path("consignments/<int:pk>/recalculate-freight/", ConsignmentRecalculateFreight.as_view(), name="consignment-recalculate-freight"),
    path("consignment-groups/", ConsignmentGroupListCreate.as_view(), name="consignment-group-list-create"),
    path("consignment-groups/<int:pk>/", ConsignmentGroupDetail.as_view(), name="consignment-group-detail"),
    path("consignment-groups/<int:pk>/recalculate-totals/", ConsignmentGroupRecalculateTotals.as_view(), name="consignment-group-recalculate-totals"),
    path("shipments/", ShipmentListCreate.as_view(), name="shipment-list-create"),
    path("shipments/<int:pk>/", ShipmentDetail.as_view(), name="shipment-detail"),
    path("shipments/<int:pk>/calculate-totals/", ShipmentCalculateTotals.as_view(), name="shipment-calculate-totals"),
    path("shipments/<int:pk>/calculate-distance/", ShipmentCalculateDistance.as_view(), name="shipment-calculate-distance"),
    path("shipments/lr/preview/", ShipmentNextLRPreview.as_view(), name="shipment-lr-preview"),
    path("shipments/<int:pk>/lr-pdf/", ShipmentLRPdfView.as_view(), name="shipment-lr-pdf"),
    path("shipment-expenses/", ShipmentExpenseListCreate.as_view(), name="shipment-expense-list-create"),
    path("shipment-expenses/<int:pk>/", ShipmentExpenseDetail.as_view(), name="shipment-expense-detail"),
    path("shipment-expenses/expense-by-autocomplete/", ShipmentExpenseByAutocomplete.as_view(), name="shipment-expense-by-autocomplete"),
    path("shipment-status/", ShipmentStatusListCreate.as_view(), name="shipment-status-list-create"),
    path("shipment-status/<int:pk>/", ShipmentStatusDetail.as_view(), name="shipment-status-detail"),
    path("driver-advances/", DriverAdvanceListCreate.as_view(), name="driver-advance-list-create"),
    path("driver-advances/<int:pk>/", DriverAdvanceDetail.as_view(), name="driver-advance-detail"),
    path("driver-advances/<int:pk>/settle/", DriverAdvanceSettle.as_view(), name="driver-advance-settle"),
    path("driver-advances/summary/", DriverAdvanceSummary.as_view(), name="driver-advance-summary"),
    path("driver-ledger/<int:driver_id>/", DriverLedgerView.as_view(), name="driver-ledger"),
    path("driver-ledger/<int:driver_id>/excel/", DriverLedgerExcelView.as_view(), name="driver-ledger-excel"),
    path("diesel/", DieselListCreate.as_view(), name="diesel-list-create"),
    path("diesel/<int:pk>/", DieselDetail.as_view(), name="diesel-detail"),
    path("diesel/summary/", DieselSummary.as_view(), name="diesel-summary"),
]
