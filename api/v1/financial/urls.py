"""
Financial API URLs powered by DRF router.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BankTransferViewSet, InvoiceViewSet, OtherExpenseViewSet, PaymentViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r"invoices", InvoiceViewSet, basename="fin-invoice")
router.register(r"payments", PaymentViewSet, basename="fin-payment")
router.register(r"transactions", TransactionViewSet, basename="fin-transaction")
router.register(r"other-expenses", OtherExpenseViewSet, basename="fin-other-expense")
router.register(r"bank-transfers", BankTransferViewSet, basename="fin-bank-transfer")

urlpatterns = [
    path("", include(router.urls)),
]
