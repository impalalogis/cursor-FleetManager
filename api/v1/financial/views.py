"""
Financial API viewsets and domain actions.
"""

from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response

from api.utils import BulkModelViewSet, StandardResultsSetPagination
from financial.models import BankTransfer, Invoice, OfficeExpense, Payment, Transaction

from .serializers import BankTransferSerializer, InvoiceSerializer, OtherExpenseSerializer, PaymentSerializer, TransactionSerializer


class BaseFinancialViewSet(BulkModelViewSet):
    authentication_classes = []
    permission_classes = []
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class InvoiceViewSet(BaseFinancialViewSet):
    queryset = Invoice.objects.select_related("shipment", "consignmentGroup").prefetch_related("payments").all().order_by(
        "-issue_date",
        "-id",
    )
    serializer_class = InvoiceSerializer
    filterset_fields = ["shipment", "consignmentGroup", "status", "is_paid", "bill_to", "issue_date", "due_date"]
    search_fields = ["invoice_id", "invoice_ref", "shipment__shipment_id", "consignmentGroup__group_id", "notes"]
    ordering_fields = ["issue_date", "due_date", "total_freight", "total_dues", "created_at", "updated_at", "id"]

    @action(detail=True, methods=["post"], url_path="calculate")
    def calculate(self, request, pk=None):
        invoice = self.get_object()
        invoice.calculate_totals()
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=["get"], url_path="financial-summary")
    def financial_summary(self, request, pk=None):
        invoice = self.get_object()
        return Response(invoice.financial_summary())

    @action(detail=True, methods=["get"], url_path="itemized-breakdown")
    def itemized_breakdown(self, request, pk=None):
        invoice = self.get_object()
        return Response(invoice.get_itemized_breakdown())


class PaymentViewSet(BaseFinancialViewSet):
    queryset = Payment.objects.select_related("invoice", "method", "from_banking_detail", "to_banking_detail").all().order_by(
        "-payment_date",
        "-id",
    )
    serializer_class = PaymentSerializer
    filterset_fields = ["invoice", "method", "payment_method", "status", "payment_date"]
    search_fields = [
        "reference_number",
        "transaction_reference",
        "utr_number",
        "transaction_id",
        "cheque_number",
        "invoice__invoice_id",
    ]
    ordering_fields = ["payment_date", "amount_paid", "created_at", "updated_at", "id"]

    @action(detail=True, methods=["post"], url_path="status-update")
    def status_update(self, request, pk=None):
        payment = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status is required."}, status=400)
        payment.status = str(new_status).upper()
        payment.save()
        return Response(self.get_serializer(payment).data)


class TransactionViewSet(BaseFinancialViewSet):
    queryset = Transaction.objects.select_related("shipment", "driver", "vehicle").all().order_by(
        "-transaction_date",
        "-created_at",
    )
    serializer_class = TransactionSerializer
    filterset_fields = ["transaction_type", "category", "shipment", "driver", "vehicle", "transaction_date"]
    search_fields = ["transaction_id", "reference_number", "description", "created_by"]
    ordering_fields = ["transaction_date", "amount", "created_at", "updated_at", "id"]

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "count": queryset.count(),
                "total_amount": queryset.aggregate(total=Sum("amount"))["total"] or 0,
                "expense_total": queryset.filter(transaction_type="expense").aggregate(total=Sum("amount"))["total"] or 0,
                "advance_total": queryset.filter(transaction_type="advance").aggregate(total=Sum("amount"))["total"] or 0,
                "revenue_total": queryset.filter(transaction_type="revenue").aggregate(total=Sum("amount"))["total"] or 0,
            }
        )

    @action(detail=False, methods=["get"], url_path="by-category")
    def by_category(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        rows = queryset.values("category").annotate(total_amount=Sum("amount")).order_by("-total_amount")
        return Response(list(rows))

    @action(detail=False, methods=["get"], url_path="monthly-summary")
    def monthly_summary(self, request):
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        if not year or not month:
            return Response({"detail": "year and month are required."}, status=400)
        return Response(Transaction.get_monthly_summary(int(year), int(month)))


class OtherExpenseViewSet(BaseFinancialViewSet):
    queryset = OfficeExpense.objects.select_related("category", "driver").all().order_by("-expense_date", "-id")
    serializer_class = OtherExpenseSerializer
    filterset_fields = ["category", "driver", "expense_date"]
    search_fields = ["description", "paid_by", "category__display_value"]
    ordering_fields = ["expense_date", "amount", "id"]


class BankTransferViewSet(BaseFinancialViewSet):
    queryset = BankTransfer.objects.select_related("from_banking_detail", "to_banking_detail").all().order_by(
        "-initiated_datetime",
        "-id",
    )
    serializer_class = BankTransferSerializer
    filterset_fields = ["transfer_type", "transfer_mode", "status", "related_shipment", "related_driver", "related_invoice"]
    search_fields = ["transaction_id", "utr_number", "reference_number", "beneficiary_name", "description"]
    ordering_fields = ["initiated_datetime", "processed_datetime", "completed_datetime", "amount", "id"]

