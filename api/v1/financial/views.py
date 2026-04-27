"""
Financial API views.
"""

import base64
from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from xhtml2pdf import pisa

from financial.models import BankTransfer, Invoice, OfficeExpense, Payment, Transaction
from financial.signals import safe_calculate_invoice_totals

from .serializers import (
    BankTransferSerializer,
    InvoiceSerializer,
    OtherExpenseSerializer,
    PaymentSerializer,
    TransactionSerializer,
)


class InvoiceListCreate(APIView):
    def get(self, request):
        queryset = Invoice.objects.select_related("shipment", "consignmentGroup").prefetch_related("payments").order_by(
            "-issue_date",
            "-id",
        )
        shipment_id = request.GET.get("shipment")
        if shipment_id:
            queryset = queryset.filter(shipment_id=shipment_id)
        status_param = request.GET.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        is_paid = request.GET.get("is_paid")
        if is_paid in {"true", "false", "1", "0"}:
            queryset = queryset.filter(is_paid=is_paid in {"true", "1"})

        serializer = InvoiceSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = InvoiceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            InvoiceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class InvoiceDetail(APIView):
    def get_object(self, pk: int):
        return Invoice.objects.select_related("shipment", "consignmentGroup").prefetch_related("payments").filter(
            pk=pk
        ).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            InvoiceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = InvoiceSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            InvoiceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceCalculateTotals(APIView):
    def post(self, request, pk: int):
        invoice = get_object_or_404(Invoice, pk=pk)
        invoice.calculate_totals()
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class InvoiceMarkStatus(APIView):
    """
    Set invoice status quickly.
    Payload:
      {"status": "PAID" | "PENDING"}
    """

    def post(self, request, pk: int):
        invoice = get_object_or_404(Invoice, pk=pk)
        status_value = (request.data.get("status") or "").upper().strip()
        if status_value not in {"PAID", "PENDING"}:
            return Response(
                {"status": "Allowed values are PAID or PENDING."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = status_value
        invoice.is_paid = status_value == "PAID"
        invoice.save(skip_calculation=True)
        return Response(
            InvoiceSerializer(invoice, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class InvoicePaymentHistory(APIView):
    def get(self, request, pk: int):
        invoice = get_object_or_404(Invoice, pk=pk)
        payments = invoice.payments.order_by("-payment_date", "-id")
        serializer = PaymentSerializer(payments, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class InvoiceSummary(APIView):
    def get(self, request):
        queryset = Invoice.objects.all()
        summary = {
            "total_invoices": queryset.count(),
            "total_dues_sum": float(queryset.aggregate(total=Sum("total_dues"))["total"] or 0),
            "paid_count": queryset.filter(is_paid=True).count(),
            "pending_count": queryset.filter(is_paid=False).count(),
            "overdue_count": queryset.filter(due_date__lt=date.today(), is_paid=False).count(),
        }
        return Response(summary, status=status.HTTP_200_OK)


class InvoiceOverdueList(APIView):
    def get(self, request):
        queryset = Invoice.objects.filter(due_date__lt=date.today(), is_paid=False).order_by("due_date")
        serializer = InvoiceSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class InvoiceUnpaidList(APIView):
    def get(self, request):
        queryset = Invoice.objects.filter(is_paid=False).order_by("-issue_date", "-id")
        serializer = InvoiceSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class InvoicePartiallyPaidList(APIView):
    def get(self, request):
        queryset = Invoice.objects.filter(
            is_paid=False,
            payment_received__gt=0,
        ).order_by("-issue_date", "-id")
        serializer = InvoiceSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class InvoicePdfView(APIView):
    """
    API equivalent of admin invoice PDF render.
    """

    def get(self, request, pk: int):
        invoice = get_object_or_404(
            Invoice.objects.select_related(
                "shipment",
                "shipment__driver",
                "shipment__vehicle",
                "shipment__consignment_group",
            ).prefetch_related(
                "shipment__consignment_group__consignments",
                "payments",
            ),
            pk=pk,
        )

        consignments = (
            invoice.shipment.consignment_group.consignments.all()
            if invoice.shipment and invoice.shipment.consignment_group
            else []
        )

        signature_uri = None
        signature_path = Path(settings.BASE_DIR) / "operations" / "static" / "images" / "authorized_signature.png"
        if signature_path.exists():
            with open(signature_path, "rb") as image_file:
                signature_uri = "data:image/png;base64," + base64.b64encode(image_file.read()).decode("utf-8")

        bill_to_party = None
        bill_to_address = None
        bill_to_gst = None
        party = None

        if invoice.bill_to == "CONSIGNOR":
            party = consignments[0].consignor if consignments else None
        elif invoice.bill_to == "CONSIGNEE":
            party = consignments[0].consignee if consignments else None
        elif invoice.bill_to == "TRANSPORTER":
            party = invoice.shipment.transporter if invoice.shipment else None
        elif invoice.bill_to == "BROKER":
            party = invoice.shipment.broker if invoice.shipment else None

        if party:
            bill_to_party = getattr(party, "organization_name", str(party))
            bill_to_address = party.get_formatted_address() if hasattr(party, "get_formatted_address") else ""
            bill_to_gst = getattr(party, "GST_NO", "")

        html = render_to_string(
            "admin/invoice/invoice_pdf.html",
            {
                "invoice": invoice,
                "shipment": invoice.shipment,
                "consignments": consignments,
                "detention_amount": invoice.detention_amount,
                "breakdown": invoice.get_itemized_breakdown(),
                "signature_uri": signature_uri,
                "bill_to_party": bill_to_party,
                "bill_to_address": bill_to_address,
                "bill_to_gst": bill_to_gst,
            },
        )

        output = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), output)
        if pdf.err:
            return Response({"detail": "Error generating PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(output.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="invoice_{invoice.invoice_id}.pdf"'
        return response


class PaymentListCreate(APIView):
    def get(self, request):
        queryset = Payment.objects.select_related(
            "invoice",
            "method",
            "from_banking_detail",
            "to_banking_detail",
        ).order_by("-payment_date", "-id")
        invoice_id = request.GET.get("invoice")
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        status_param = request.GET.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        serializer = PaymentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if instance.invoice_id:
            safe_calculate_invoice_totals(instance.invoice)
        return Response(
            PaymentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentDetail(APIView):
    def get_object(self, pk: int):
        return Payment.objects.select_related("invoice", "method").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            PaymentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if instance.invoice_id:
            safe_calculate_invoice_totals(instance.invoice)
        return Response(
            PaymentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        invoice = instance.invoice
        instance.delete()
        if invoice:
            safe_calculate_invoice_totals(invoice)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentMarkCompleted(APIView):
    def post(self, request, pk: int):
        payment = get_object_or_404(Payment, pk=pk)
        payment.status = "COMPLETED"
        payment.save()
        if payment.invoice_id:
            safe_calculate_invoice_totals(payment.invoice)
        return Response(
            PaymentSerializer(payment, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class PaymentSummary(APIView):
    def get(self, request):
        queryset = Payment.objects.all()
        summary = {
            "total_payments": queryset.count(),
            "total_amount": float(queryset.aggregate(total=Sum("amount_paid"))["total"] or 0),
            "completed_count": queryset.filter(status="COMPLETED").count(),
            "pending_count": queryset.filter(status="PENDING").count(),
        }
        return Response(summary, status=status.HTTP_200_OK)


class PaymentPendingList(APIView):
    def get(self, request):
        queryset = Payment.objects.filter(status="PENDING").order_by("-payment_date", "-id")
        serializer = PaymentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentCompletedList(APIView):
    def get(self, request):
        queryset = Payment.objects.filter(status="COMPLETED").order_by("-payment_date", "-id")
        serializer = PaymentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentByMethodList(APIView):
    def get(self, request):
        method = request.GET.get("method")
        if not method:
            return Response({"method": "This query param is required."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = Payment.objects.filter(Q(method_id=method) | Q(payment_method=method)).order_by(
            "-payment_date",
            "-id",
        )
        serializer = PaymentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TransactionListCreate(APIView):
    def get(self, request):
        queryset = Transaction.objects.select_related("shipment", "driver", "vehicle").order_by(
            "-transaction_date",
            "-created_at",
        )
        category = request.GET.get("category")
        if category:
            queryset = queryset.filter(category=category)
        tx_type = request.GET.get("transaction_type")
        if tx_type:
            queryset = queryset.filter(transaction_type=tx_type)
        serializer = TransactionSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TransactionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TransactionSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TransactionDetail(APIView):
    def get_object(self, pk: int):
        return Transaction.objects.select_related("shipment", "driver", "vehicle").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            TransactionSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TransactionSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TransactionSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OtherExpenseListCreate(APIView):
    def get(self, request):
        queryset = OfficeExpense.objects.select_related("category", "driver").order_by("-expense_date", "-id")
        category = request.GET.get("category")
        if category:
            queryset = queryset.filter(category_id=category)
        serializer = OtherExpenseSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OtherExpenseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            OtherExpenseSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OtherExpenseDetail(APIView):
    def get_object(self, pk: int):
        return OfficeExpense.objects.select_related("category", "driver").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            OtherExpenseSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OtherExpenseSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            OtherExpenseSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BankTransferListCreate(APIView):
    def get(self, request):
        queryset = BankTransfer.objects.select_related("from_banking_detail", "to_banking_detail").order_by(
            "-initiated_datetime",
            "-id",
        )
        status_param = request.GET.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        serializer = BankTransferSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = BankTransferSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            BankTransferSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class BankTransferDetail(APIView):
    def get_object(self, pk: int):
        return BankTransfer.objects.select_related("from_banking_detail", "to_banking_detail").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            BankTransferSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BankTransferSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            BankTransferSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BankTransferMarkCompleted(APIView):
    def post(self, request, pk: int):
        transfer = get_object_or_404(BankTransfer, pk=pk)
        transfer.status = "COMPLETED"
        transfer.save()
        return Response(
            BankTransferSerializer(transfer, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class BankTransferPendingList(APIView):
    def get(self, request):
        queryset = BankTransfer.objects.filter(status="PENDING").order_by("-initiated_datetime", "-id")
        serializer = BankTransferSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class BankTransferCompletedList(APIView):
    def get(self, request):
        queryset = BankTransfer.objects.filter(status="COMPLETED").order_by("-initiated_datetime", "-id")
        serializer = BankTransferSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
