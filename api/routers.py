"""
Project-level API router registry helper.
"""

from rest_framework.routers import DefaultRouter

from api.v1.configuration.views import (
    BankingDetailViewSet as ConfigurationBankingDetailViewSet,
    ChoiceViewSet as ConfigurationChoiceViewSet,
    LocationViewSet as ConfigurationLocationViewSet,
    PostalInfoViewSet as ConfigurationPostalInfoViewSet,
    RouteViewSet as ConfigurationRouteViewSet,
)
from api.v1.entity.views import (
    DriverDocumentViewSet,
    DriverViewSet,
    OrganizationDocumentViewSet,
    OrganizationViewSet,
    VehicleDocumentViewSet,
    VehicleViewSet,
)
from api.v1.financial.views import (
    BankTransferViewSet,
    InvoiceViewSet,
    OtherExpenseViewSet,
    PaymentViewSet,
    TransactionViewSet,
)
from api.v1.maintenance.views import MaintenanceRecordViewSet, TyreTransactionViewSet, TyreViewSet
from api.v1.operations.views import (
    ConsignmentGroupViewSet,
    ConsignmentViewSet,
    DieselViewSet,
    DriverAdvanceViewSet,
    ShipmentExpenseViewSet,
    ShipmentStatusViewSet,
    ShipmentViewSet,
)


def build_api_v1_router() -> DefaultRouter:
    router = DefaultRouter()

    # configuration
    router.register(r"configuration/choices", ConfigurationChoiceViewSet, basename="cfg-choice")
    router.register(r"configuration/locations", ConfigurationLocationViewSet, basename="cfg-location")
    router.register(r"configuration/routes", ConfigurationRouteViewSet, basename="cfg-route")
    router.register(r"configuration/postal-info", ConfigurationPostalInfoViewSet, basename="cfg-postal-info")
    router.register(r"configuration/banking-details", ConfigurationBankingDetailViewSet, basename="cfg-banking-detail")

    # entity
    router.register(r"entity/organizations", OrganizationViewSet, basename="entity-organization")
    router.register(r"entity/organization-documents", OrganizationDocumentViewSet, basename="entity-organization-document")
    router.register(r"entity/drivers", DriverViewSet, basename="entity-driver")
    router.register(r"entity/driver-documents", DriverDocumentViewSet, basename="entity-driver-document")
    router.register(r"entity/vehicles", VehicleViewSet, basename="entity-vehicle")
    router.register(r"entity/vehicle-documents", VehicleDocumentViewSet, basename="entity-vehicle-document")

    # operations
    router.register(r"operations/consignments", ConsignmentViewSet, basename="ops-consignment")
    router.register(r"operations/consignment-groups", ConsignmentGroupViewSet, basename="ops-consignment-group")
    router.register(r"operations/shipments", ShipmentViewSet, basename="ops-shipment")
    router.register(r"operations/shipment-expenses", ShipmentExpenseViewSet, basename="ops-shipment-expense")
    router.register(r"operations/shipment-status", ShipmentStatusViewSet, basename="ops-shipment-status")
    router.register(r"operations/driver-advances", DriverAdvanceViewSet, basename="ops-driver-advance")
    router.register(r"operations/diesel", DieselViewSet, basename="ops-diesel")

    # financial
    router.register(r"financial/invoices", InvoiceViewSet, basename="fin-invoice")
    router.register(r"financial/payments", PaymentViewSet, basename="fin-payment")
    router.register(r"financial/transactions", TransactionViewSet, basename="fin-transaction")
    router.register(r"financial/other-expenses", OtherExpenseViewSet, basename="fin-other-expense")
    router.register(r"financial/bank-transfers", BankTransferViewSet, basename="fin-bank-transfer")

    # maintenance
    router.register(r"maintenance/maintenance-records", MaintenanceRecordViewSet, basename="maint-record")
    router.register(r"maintenance/tyres", TyreViewSet, basename="maint-tyre")
    router.register(r"maintenance/tyre-transactions", TyreTransactionViewSet, basename="maint-tyre-transaction")

    return router

