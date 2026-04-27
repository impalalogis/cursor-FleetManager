"""
Operations API views.
"""

import base64
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from xhtml2pdf import pisa

import openpyxl

from entity.models import Driver, Organization
from operations.models import (
    Consignment,
    ConsignmentGroup,
    Diesel,
    DriverAdvance,
    Shipment,
    ShipmentExpense,
    ShipmentStatus,
)

from .serializers import (
    ConsignmentGroupSerializer,
    ConsignmentSerializer,
    DieselSerializer,
    DriverAdvanceSerializer,
    ShipmentExpenseSerializer,
    ShipmentSerializer,
    ShipmentStatusSerializer,
)


def _safe_decimal(value):
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _apply_status_to_shipment(status_entry: ShipmentStatus):
    """
    Keep API behavior aligned with ShipmentStatusAdmin.save_model().
    """
    shipment = status_entry.shipment
    if not shipment:
        return

    raw_status = ""
    if status_entry.status:
        raw_status = (
            getattr(status_entry.status, "internal_value", None)
            or getattr(status_entry.status, "name", None)
            or ""
        )
    status_name = raw_status.replace(" ", "").replace("-", "").lower()

    updates = []

    # 1) Departure -> actual_departure + (optional) odometer_start from notes
    if status_name in {"03_departure", "departure", "departed"}:
        shipment.actual_departure = status_entry.effective_date
        updates.append("actual_departure")
        if status_entry.notes:
            try:
                shipment.odometer_start = Decimal(status_entry.notes.strip())
                updates.append("odometer_start")
            except Exception:
                pass

    # 2) Reached -> actual_arrival + (optional) odometer_start from notes (admin parity)
    elif status_name in {"04_reached", "reached", "arrived"}:
        shipment.actual_arrival = status_entry.effective_date
        updates.append("actual_arrival")
        if status_entry.notes:
            try:
                shipment.odometer_start = Decimal(status_entry.notes.strip())
                updates.append("odometer_start")
            except Exception:
                pass

    # 3) Completed -> (optional) odometer_end from notes
    elif status_name in {"07_completed", "completed", "finished"}:
        if status_entry.notes:
            try:
                shipment.odometer_end = Decimal(status_entry.notes.strip())
                updates.append("odometer_end")
            except Exception:
                pass

    # 4) auto-calc distance
    if shipment.odometer_start is not None and shipment.odometer_end is not None:
        shipment.total_distance = shipment.odometer_end - shipment.odometer_start
        updates.append("total_distance")

    if updates:
        shipment.save(update_fields=list(set(updates)))


def _build_driver_ledger(driver, from_date=None, to_date=None):
    """
    Mirror DriverAdvanceAdmin._build_driver_ledger.
    """
    driver_ct = ContentType.objects.get_for_model(driver)
    rows = []

    advances_qs = DriverAdvance.objects.filter(driver=driver)
    if from_date:
        advances_qs = advances_qs.filter(date__gte=from_date)
    if to_date:
        advances_qs = advances_qs.filter(date__lte=to_date)

    for adv in advances_qs.values("date", "amount", "description", "shipment__shipment_id"):
        rows.append(
            {
                "date": adv["date"],
                "type": "Advance",
                "shipment": adv["shipment__shipment_id"],
                "debit": Decimal("0"),
                "credit": _safe_decimal(adv["amount"]),
                "description": adv["description"] or "",
            }
        )

    expenses_qs = ShipmentExpense.objects.filter(content_type=driver_ct, object_id=driver.id)
    if from_date:
        expenses_qs = expenses_qs.filter(expense_date__gte=from_date)
    if to_date:
        expenses_qs = expenses_qs.filter(expense_date__lte=to_date)

    for exp in expenses_qs.values(
        "expense_date",
        "amount",
        "description",
        "shipment__shipment_id",
        "expense_type__display_value",
    ):
        rows.append(
            {
                "date": exp["expense_date"],
                "type": exp["expense_type__display_value"] or "Shipment Expense",
                "shipment": exp["shipment__shipment_id"],
                "debit": _safe_decimal(exp["amount"]),
                "credit": Decimal("0"),
                "description": exp["description"] or "",
            }
        )

    rows.sort(key=lambda item: (item["date"] or "", item["type"]))
    running = Decimal("0")
    for row in rows:
        running += row["credit"]
        running -= row["debit"]
        row["running_balance"] = running

    return {
        "rows": rows,
        "opening_balance": Decimal("0"),
        "closing_balance": running,
    }


class ConsignmentListCreate(APIView):
    def get(self, request):
        queryset = Consignment.objects.select_related(
            "consignor",
            "consignee",
            "material_type",
            "weight_unit",
            "packaging_type",
            "vehicle_type",
            "freight_mode",
            "from_location",
            "to_location",
        ).order_by("-created_at")

        q = request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(consignment_id__icontains=q)
                | Q(consignor__organization_name__icontains=q)
                | Q(consignee__organization_name__icontains=q)
            )

        consignor_id = request.GET.get("consignor")
        if consignor_id:
            queryset = queryset.filter(consignor_id=consignor_id)

        consignee_id = request.GET.get("consignee")
        if consignee_id:
            queryset = queryset.filter(consignee_id=consignee_id)

        serializer = ConsignmentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ConsignmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ConsignmentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConsignmentDetail(APIView):
    def get_object(self, pk: int):
        return Consignment.objects.select_related("consignor", "consignee").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            ConsignmentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ConsignmentSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ConsignmentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsignmentRecalculateFreight(APIView):
    def post(self, request, pk: int):
        instance = get_object_or_404(Consignment, pk=pk)
        instance.save()  # re-run model calculation path
        return Response(
            {
                "id": instance.id,
                "consignment_id": instance.consignment_id,
                "total_freight": instance.total_freight,
            },
            status=status.HTTP_200_OK,
        )


class ConsignmentGroupListCreate(APIView):
    def get(self, request):
        queryset = ConsignmentGroup.objects.prefetch_related("consignments").order_by("-created_at")
        q = request.GET.get("q")
        if q:
            queryset = queryset.filter(group_id__icontains=q)
        serializer = ConsignmentGroupSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ConsignmentGroupSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ConsignmentGroupSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConsignmentGroupDetail(APIView):
    def get_object(self, pk: int):
        return ConsignmentGroup.objects.prefetch_related("consignments").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            ConsignmentGroupSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ConsignmentGroupSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ConsignmentGroupSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsignmentGroupRecalculateTotals(APIView):
    def post(self, request, pk: int):
        instance = get_object_or_404(ConsignmentGroup, pk=pk)
        instance.calculate_totals()
        return Response(
            {
                "id": instance.id,
                "group_id": instance.group_id,
                "total_weight": instance.total_weight,
                "total_amount": instance.total_amount,
            },
            status=status.HTTP_200_OK,
        )


class ShipmentListCreate(APIView):
    def get(self, request):
        queryset = Shipment.objects.select_related(
            "consignment_group",
            "vehicle",
            "driver",
            "co_driver",
            "transporter",
            "broker",
            "planned_route",
            "actual_route",
        ).order_by("-created_at")

        q = request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(shipment_id__icontains=q)
                | Q(consignment_group__group_id__icontains=q)
                | Q(vehicle__registration_number__icontains=q)
            )

        vehicle = request.GET.get("vehicle")
        if vehicle:
            queryset = queryset.filter(vehicle_id=vehicle)

        driver = request.GET.get("driver")
        if driver:
            queryset = queryset.filter(driver_id=driver)

        status_value = request.GET.get("status")
        if status_value:
            queryset = queryset.filter(status_logs__status__internal_value=status_value).distinct()

        serializer = ShipmentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ShipmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ShipmentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ShipmentDetail(APIView):
    def get_object(self, pk: int):
        return Shipment.objects.select_related("consignment_group", "vehicle", "driver").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            ShipmentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShipmentSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ShipmentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShipmentCalculateTotals(APIView):
    def post(self, request, pk: int):
        shipment = get_object_or_404(Shipment, pk=pk)
        shipment.calculate_totals()
        return Response(
            {
                "id": shipment.id,
                "shipment_id": shipment.shipment_id,
                "total_freight_amount": shipment.total_freight_amount,
            },
            status=status.HTTP_200_OK,
        )


class ShipmentCalculateDistance(APIView):
    def post(self, request, pk: int):
        shipment = get_object_or_404(Shipment, pk=pk)
        total_distance = shipment.calculate_distance()
        shipment.save(update_fields=["total_distance"])
        return Response(
            {
                "id": shipment.id,
                "shipment_id": shipment.shipment_id,
                "total_distance": total_distance,
            },
            status=status.HTTP_200_OK,
        )


class ShipmentNextLRPreview(APIView):
    def get(self, request):
        shipment_id = request.GET.get("shipment_id")
        exclude_pk = int(shipment_id) if shipment_id and shipment_id.isdigit() else None
        return Response({"lr_no": Shipment.get_next_lr_no(exclude_pk=exclude_pk)}, status=status.HTTP_200_OK)


class ShipmentLRPdfView(APIView):
    def get(self, request, pk: int):
        shipment = get_object_or_404(
            Shipment.objects.select_related(
                "consignment_group",
                "vehicle",
                "driver",
            ).prefetch_related(
                "consignment_group__consignments__consignor",
                "consignment_group__consignments__consignee",
                "consignment_group__consignments__from_location",
                "consignment_group__consignments__to_location",
                "consignment_group__consignments__material_type",
                "consignment_group__consignments__weight_unit",
            ),
            pk=pk,
        )

        consignments = shipment.consignment_group.consignments.all() if shipment.consignment_group else []
        total_amount = shipment.total_freight_amount or Decimal("0")
        advance = shipment.freight_advance or Decimal("0")
        to_pay = total_amount - advance

        signature_uri = None
        signature_path = Path(settings.BASE_DIR) / "operations" / "static" / "images" / "authorized_signature.png"
        if signature_path.exists():
            with open(signature_path, "rb") as image_file:
                signature_uri = "data:image/png;base64," + base64.b64encode(image_file.read()).decode("utf-8")

        html = render_to_string(
            "admin/shipments/shipment_invoice.html",
            {
                "shipment": shipment,
                "consignments": consignments,
                "total_amount": total_amount,
                "advance": advance,
                "to_pay": to_pay,
                "signature_uri": signature_uri,
            },
        )

        output = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), output)
        if pdf.err:
            return Response({"detail": "Error generating PDF"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(output.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="shipment_invoice_{shipment.shipment_id}.pdf"'
        return response


class ShipmentExpenseListCreate(APIView):
    def get(self, request):
        queryset = ShipmentExpense.objects.select_related("shipment", "expense_type", "content_type").order_by(
            "-expense_date",
            "-id",
        )

        shipment_id = request.GET.get("shipment")
        if shipment_id:
            queryset = queryset.filter(shipment_id=shipment_id)

        expense_type_id = request.GET.get("expense_type")
        if expense_type_id:
            queryset = queryset.filter(expense_type_id=expense_type_id)

        driver_id = request.GET.get("driver")
        if driver_id:
            driver_ct = ContentType.objects.get_for_model(Driver)
            queryset = queryset.filter(content_type=driver_ct, object_id=driver_id)

        owner_id = request.GET.get("owner")
        if owner_id:
            owner_ct = ContentType.objects.get_for_model(Organization)
            queryset = queryset.filter(content_type=owner_ct, object_id=owner_id)

        serializer = ShipmentExpenseSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ShipmentExpenseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ShipmentExpenseSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ShipmentExpenseDetail(APIView):
    def get_object(self, pk: int):
        return ShipmentExpense.objects.select_related("shipment", "expense_type", "content_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            ShipmentExpenseSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShipmentExpenseSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            ShipmentExpenseSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShipmentExpenseByAutocomplete(APIView):
    def get(self, request):
        term = (request.GET.get("term") or request.GET.get("q") or "").strip()
        results = []

        drivers = Driver.objects.all()
        if term:
            drivers = drivers.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(phone_number__icontains=term)
            )
        for driver in drivers.order_by("first_name", "last_name")[:20]:
            results.append(
                {
                    "id": f"driver_{driver.id}",
                    "text": f"Driver: {driver.first_name} {(driver.last_name or '').strip()}".strip(),
                }
            )

        owners = Organization.objects.filter(organization_type__internal_value="OWNER")
        if term:
            owners = owners.filter(organization_name__icontains=term)
        for owner in owners.order_by("organization_name")[:20]:
            results.append({"id": f"owner_{owner.id}", "text": f"Owner: {owner.organization_name}"})

        return Response({"results": results}, status=status.HTTP_200_OK)


class ShipmentStatusListCreate(APIView):
    def get(self, request):
        queryset = ShipmentStatus.objects.select_related("shipment", "status", "shipment_doc_type").order_by(
            "-effective_date",
            "-id",
        )

        shipment_id = request.GET.get("shipment")
        if shipment_id:
            queryset = queryset.filter(shipment_id=shipment_id)

        status_id = request.GET.get("status")
        if status_id:
            queryset = queryset.filter(status_id=status_id)

        serializer = ShipmentStatusSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ShipmentStatusSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        _apply_status_to_shipment(instance)
        return Response(
            ShipmentStatusSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ShipmentStatusDetail(APIView):
    def get_object(self, pk: int):
        return ShipmentStatus.objects.select_related("shipment", "status", "shipment_doc_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            ShipmentStatusSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShipmentStatusSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        _apply_status_to_shipment(instance)
        return Response(
            ShipmentStatusSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverAdvanceListCreate(APIView):
    def get(self, request):
        queryset = DriverAdvance.objects.select_related("driver", "shipment", "content_type").order_by("-date", "-id")

        driver_id = request.GET.get("driver")
        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)

        shipment_id = request.GET.get("shipment")
        if shipment_id:
            queryset = queryset.filter(shipment_id=shipment_id)

        serializer = DriverAdvanceSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        use_carry_forward = str(request.data.get("use_carry_forward", "")).lower() in {"1", "true", "yes"}
        if use_carry_forward:
            driver_id = request.data.get("driver")
            driver = Driver.objects.filter(pk=driver_id).first()
            if not driver:
                return Response({"driver": "Invalid driver id."}, status=status.HTTP_400_BAD_REQUEST)

            shipment = None
            shipment_id = request.data.get("shipment")
            if shipment_id:
                shipment = Shipment.objects.filter(pk=shipment_id).first()
                if not shipment:
                    return Response({"shipment": "Invalid shipment id."}, status=status.HTTP_400_BAD_REQUEST)

            amount = request.data.get("amount")
            if amount in (None, ""):
                return Response({"amount": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

            instance = DriverAdvance.create_driver_advance(
                driver=driver,
                shipment=shipment,
                amount=amount,
                description=request.data.get("description", ""),
            )
            return Response(
                DriverAdvanceSerializer(instance, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        serializer = DriverAdvanceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DriverAdvanceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DriverAdvanceDetail(APIView):
    def get_object(self, pk: int):
        return DriverAdvance.objects.select_related("driver", "shipment", "content_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            DriverAdvanceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DriverAdvanceSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DriverAdvanceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverAdvanceSettle(APIView):
    def post(self, request, pk: int):
        instance = DriverAdvance.objects.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.settle_and_carry_forward()
        return Response(
            DriverAdvanceSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class DriverAdvanceSummary(APIView):
    def get(self, request):
        driver_id = request.GET.get("driver")
        if not driver_id:
            return Response({"driver": "This query param is required."}, status=status.HTTP_400_BAD_REQUEST)

        driver = Driver.objects.filter(pk=driver_id).first()
        if not driver:
            return Response({"driver": "Invalid driver id."}, status=status.HTTP_400_BAD_REQUEST)

        shipment = None
        shipment_id = request.GET.get("shipment")
        if shipment_id:
            shipment = Shipment.objects.filter(pk=shipment_id).first()
            if not shipment:
                return Response({"shipment": "Invalid shipment id."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DriverAdvance.get_driver_summary(driver, shipment), status=status.HTTP_200_OK)


class DriverLedgerView(APIView):
    def get(self, request, driver_id: int):
        driver = get_object_or_404(Driver, pk=driver_id)
        from_date = request.GET.get("from")
        to_date = request.GET.get("to")
        ledger = _build_driver_ledger(driver, from_date=from_date, to_date=to_date)
        return Response(ledger, status=status.HTTP_200_OK)


class DriverLedgerExcelView(APIView):
    def get(self, request, driver_id: int):
        driver = get_object_or_404(Driver, pk=driver_id)
        ledger = _build_driver_ledger(
            driver,
            from_date=request.GET.get("from"),
            to_date=request.GET.get("to"),
        )

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Driver Ledger"
        sheet.append(
            [
                "Date",
                "Type",
                "Shipment",
                "Debit (₹)",
                "Credit (₹)",
                "Running Balance (₹)",
                "Description",
            ]
        )
        for row in ledger["rows"]:
            sheet.append(
                [
                    row["date"],
                    row["type"],
                    row["shipment"],
                    float(row["debit"]),
                    float(row["credit"]),
                    float(row["running_balance"]),
                    row["description"],
                ]
            )

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="driver_ledger_{driver_id}.xlsx"'
        workbook.save(response)
        return response


class DieselListCreate(APIView):
    def get(self, request):
        queryset = Diesel.objects.select_related("vehicle", "driver", "location").order_by("-date", "-id")

        vehicle = request.GET.get("vehicle")
        if vehicle:
            queryset = queryset.filter(vehicle_id=vehicle)
        driver = request.GET.get("driver")
        if driver:
            queryset = queryset.filter(driver_id=driver)
        payment_mode = request.GET.get("payment_mode")
        if payment_mode:
            queryset = queryset.filter(payment_mode=payment_mode)

        serializer = DieselSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DieselSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DieselSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DieselDetail(APIView):
    def get_object(self, pk: int):
        return Diesel.objects.select_related("vehicle", "driver", "location").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            DieselSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DieselSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DieselSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DieselSummary(APIView):
    def get(self, request):
        queryset = Diesel.objects.all()
        totals = queryset.aggregate(
            total_qty=Sum("quantity"),
            total_amount=Sum("total_price"),
            total_payment=Sum("payment"),
        )
        return Response(totals, status=status.HTTP_200_OK)
