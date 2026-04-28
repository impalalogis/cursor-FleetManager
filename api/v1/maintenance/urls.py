"""
Maintenance API URLs powered by DRF router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MaintenanceRecordViewSet, TyreTransactionViewSet, TyreViewSet

router = DefaultRouter()
router.register(r"maintenance-records", MaintenanceRecordViewSet, basename="maint-record")
router.register(r"tyres", TyreViewSet, basename="maint-tyre")
router.register(r"tyre-transactions", TyreTransactionViewSet, basename="maint-tyre-transaction")

urlpatterns = [
    path("", include(router.urls)),
]
