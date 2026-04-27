"""
Maintenance API URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MaintenanceRecordViewSet, TyreViewSet, TyreTransactionViewSet
)

router = DefaultRouter()
router.register(r'maintenance-records', MaintenanceRecordViewSet)
router.register(r'tyres', TyreViewSet)
router.register(r'tyre-transactions', TyreTransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]