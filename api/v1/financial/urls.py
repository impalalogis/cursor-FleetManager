"""
Financial API URLs.
"""

from django.urls import path

from .views import (
    BankTransferDetail,
    BankTransferListCreate,
    BankTransferMarkCompleted,
    InvoiceCalculateTotals,
    InvoiceDetail,
    InvoiceListCreate,
    InvoiceMarkStatus,
    InvoicePaymentHistory,
    InvoicePdfView,
    InvoiceSummary,
    OtherExpenseDetail,
    OtherExpenseListCreate,
    PaymentDetail,
    PaymentListCreate,
    PaymentMarkCompleted,
    PaymentSummary,
    TransactionDetail,
    TransactionListCreate,
)

urlpatterns = [
    path("invoices/", InvoiceListCreate.as_view(), name="invoice-list-create"),
    path("invoices/<int:pk>/", InvoiceDetail.as_view(), name="invoice-detail"),
    path("invoices/<int:pk>/calculate-totals/", InvoiceCalculateTotals.as_view(), name="invoice-calculate-totals"),
    path("invoices/<int:pk>/mark-status/", InvoiceMarkStatus.as_view(), name="invoice-mark-status"),
    path("invoices/<int:pk>/payment-history/", InvoicePaymentHistory.as_view(), name="invoice-payment-history"),
    path("invoices/<int:pk>/pdf/", InvoicePdfView.as_view(), name="invoice-pdf"),
    path("invoices/summary/", InvoiceSummary.as_view(), name="invoice-summary"),
    path("payments/", PaymentListCreate.as_view(), name="payment-list-create"),
    path("payments/<int:pk>/", PaymentDetail.as_view(), name="payment-detail"),
    path("payments/<int:pk>/mark-completed/", PaymentMarkCompleted.as_view(), name="payment-mark-completed"),
    path("payments/summary/", PaymentSummary.as_view(), name="payment-summary"),
    path("transactions/", TransactionListCreate.as_view(), name="transaction-list-create"),
    path("transactions/<int:pk>/", TransactionDetail.as_view(), name="transaction-detail"),
    path("other-expenses/", OtherExpenseListCreate.as_view(), name="other-expense-list-create"),
    path("other-expenses/<int:pk>/", OtherExpenseDetail.as_view(), name="other-expense-detail"),
    path("bank-transfers/", BankTransferListCreate.as_view(), name="bank-transfer-list-create"),
    path("bank-transfers/<int:pk>/", BankTransferDetail.as_view(), name="bank-transfer-detail"),
    path(
        "bank-transfers/<int:pk>/mark-completed/",
        BankTransferMarkCompleted.as_view(),
        name="bank-transfer-mark-completed",
    ),
]
