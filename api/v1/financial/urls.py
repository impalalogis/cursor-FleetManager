"""
Financial API URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InvoiceViewSet, PaymentViewSet, TransactionViewSet,
    OtherExpenseViewSet, BankTransferViewSet
)

router = DefaultRouter()
router.register(r'invoices', InvoiceViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'other-expenses', OtherExpenseViewSet)
router.register(r'bank-transfers', BankTransferViewSet)

urlpatterns = [
    path('', include(router.urls)),
]