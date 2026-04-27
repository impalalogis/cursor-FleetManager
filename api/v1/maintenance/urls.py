"""
Maintenance API URLs.
"""

from django.urls import path

from .views import (
    MaintenanceDueSoon,
    MaintenanceOverdue,
    MaintenanceRecordDetail,
    MaintenanceRecordListCreate,
    TyreDetail,
    TyreListCreate,
    TyreNeedsReplacement,
    TyreTransactionDetail,
    TyreTransactionListCreate,
)

urlpatterns = [
    path("maintenance-records/", MaintenanceRecordListCreate.as_view(), name="maintenance-record-list-create"),
    path("maintenance-records/<int:pk>/", MaintenanceRecordDetail.as_view(), name="maintenance-record-detail"),
    path("maintenance-records/due-soon/", MaintenanceDueSoon.as_view(), name="maintenance-record-due-soon"),
    path("maintenance-records/overdue/", MaintenanceOverdue.as_view(), name="maintenance-record-overdue"),
    path("tyres/", TyreListCreate.as_view(), name="tyre-list-create"),
    path("tyres/<int:pk>/", TyreDetail.as_view(), name="tyre-detail"),
    path("tyres/needs-replacement/", TyreNeedsReplacement.as_view(), name="tyre-needs-replacement"),
    path("tyre-transactions/", TyreTransactionListCreate.as_view(), name="tyre-transaction-list-create"),
    path("tyre-transactions/<int:pk>/", TyreTransactionDetail.as_view(), name="tyre-transaction-detail"),
]
