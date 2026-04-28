"""
Operations API viewsets and domain actions.
"""

from decimal import Decimal
from io import BytesIO

import openpyxl
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response

from api.utils import BulkModelViewSet, StandardResultsSetPagination
from financial.models import Invoice
from operations.models import Consignment, ConsignmentGroup, Diesel, DriverAdvance, Shipment, ShipmentExpense, ShipmentStatus

from .serializers import (
    ConsignmentGroupSerializer,
    ConsignmentSerializer,
    DieselSerializer,
    DriverAdvanceSerializer,
    ShipmentExpenseSerializer,
    ShipmentSerializer,
    ShipmentStatusSerializer,
)


class BaseOperationsViewSet(BulkModelViewSet):
    authentication_classes = []
    permission_classes = []
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class ConsignmentViewSet(BaseOperationsViewSet):
    queryset = Consignment.objects.select_related(
        "consignor",
        "consignee",
        "material_type",
        "vehicle_type",
        "freight_mode",
    ).all().order_by("-created_at")
    serializer_class = ConsignmentSerializer
    filterset_fields = ["consignor", "consignee", "schedule_date", "material_type", "vehicle_type", "freight_mode"]
    search_fields = [
        "consignment_id",
        "consignor__organization_name",
        "consignee__organization_name",
        "material_type__display_value",
        "vehicle_type__display_value",
    ]
    ordering_fields = ["created_at", "schedule_date", "expected_delivery_date", "total_freight", "weight"]

    @action(detail=False, methods=["get"], url_path="search")
    def domain_search(self, request):
        queryset = self.get_queryset()
        params = request.query_params

        consignor = params.get("consignor")
        if consignor:
            queryset = queryset.filter(consignor_id=consignor)

        consignee = params.get("consignee")
        if consignee:
            queryset = queryset.filter(consignee_id=consignee)

        material_type = params.get("material_type")
        if material_type:
            queryset = queryset.filter(material_type_id=material_type)

        vehicle_type = params.get("vehicle_type")
        if vehicle_type:
            queryset = queryset.filter(vehicle_type_id=vehicle_type)

        date_from = params.get("from")
        if date_from:
            queryset = queryset.filter(schedule_date__gte=date_from)
        date_to = params.get("to")
        if date_to:
            queryset = queryset.filter(schedule_date__lte=date_to)

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True) if page is not None else self.get_serializer(queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ConsignmentGroupViewSet(BaseOperationsViewSet):
    queryset = ConsignmentGroup.objects.prefetch_related("consignments").all().order_by("-created_at")
    serializer_class = ConsignmentGroupSerializer
    filterset_fields = ["planned_dispatch_date", "actual_dispatch_date"]
    search_fields = ["group_id"]
    ordering_fields = ["created_at", "planned_dispatch_date", "total_weight", "total_amount", "group_id"]

    @action(detail=True, methods=["get"], url_path="consignments")
    def consignments(self, request, pk=None):
        group = self.get_object()
        qs = group.consignments.all().order_by("-created_at")
        page = self.paginate_queryset(qs)
        serializer = ConsignmentSerializer(page, many=True) if page is not None else ConsignmentSerializer(qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="calculate-totals")
    def calculate_totals(self, request, pk=None):
        group = self.get_object()
        group.calculate_totals()
        return Response(self.get_serializer(group).data)


class ShipmentViewSet(BaseOperationsViewSet):
    queryset = Shipment.objects.select_related(
        "consignment_group",
        "vehicle",
        "driver",
        "co_driver",
        "transporter",
        "broker",
        "planned_route",
        "actual_route",
    ).all().order_by("-created_at")
    serializer_class = ShipmentSerializer
    filterset_fields = [
        "consignment_group",
        "vehicle",
        "driver",
        "co_driver",
        "transporter",
        "broker",
        "planned_route",
        "actual_route",
    ]
    search_fields = [
        "shipment_id",
        "lr_no",
        "invoice_no",
        "e_way_bill",
        "vehicle__registration_number",
        "driver__first_name",
        "driver__last_name",
        "consignment_group__group_id",
    ]
    ordering_fields = [
        "created_at",
        "planned_departure",
        "actual_departure",
        "planned_arrival",
        "actual_arrival",
        "total_distance",
        "total_freight_amount",
    ]

    @action(detail=True, methods=["get"], url_path="expenses")
    def expenses(self, request, pk=None):
        shipment = self.get_object()
        qs = ShipmentExpense.objects.filter(shipment=shipment).order_by("-expense_date", "-id")
        page = self.paginate_queryset(qs)
        serializer = ShipmentExpenseSerializer(page, many=True) if page is not None else ShipmentExpenseSerializer(qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="advance-summary")
    def advance_summary(self, request, pk=None):
        shipment = self.get_object()
        advances = DriverAdvance.objects.filter(shipment=shipment)
        total_advance = sum((row.amount or Decimal("0")) for row in advances)
        unsettled = advances.filter(is_settled=False).count()
        return Response(
            {
                "shipment_id": shipment.id,
                "total_advance": total_advance,
                "advance_count": advances.count(),
                "unsettled_count": unsettled,
            }
        )

    @action(detail=True, methods=["get"], url_path="route-summary")
    def route_summary(self, request, pk=None):
        shipment = self.get_object()
        return Response({"shipment_id": shipment.id, "route_summary": shipment.get_route_summary()})

    @action(detail=True, methods=["get"], url_path="status-history")
    def status_history(self, request, pk=None):
        shipment = self.get_object()
        qs = ShipmentStatus.objects.filter(shipment=shipment).order_by("-effective_date", "-id")
        page = self.paginate_queryset(qs)
        serializer = ShipmentStatusSerializer(page, many=True) if page is not None else ShipmentStatusSerializer(qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ShipmentExpenseViewSet(BaseOperationsViewSet):
    queryset = ShipmentExpense.objects.select_related("shipment", "expense_type", "content_type").all().order_by(
        "-expense_date",
        "-id",
    )
    serializer_class = ShipmentExpenseSerializer
    filterset_fields = ["shipment", "expense_type", "content_type", "object_id", "expense_date"]
    search_fields = ["description", "shipment__shipment_id", "shipment__vehicle__registration_number"]
    ordering_fields = ["expense_date", "amount", "id"]


class ShipmentStatusViewSet(BaseOperationsViewSet):
    queryset = ShipmentStatus.objects.select_related("shipment", "status", "shipment_doc_type").all().order_by(
        "-effective_date",
        "-id",
    )
    serializer_class = ShipmentStatusSerializer
    filterset_fields = ["shipment", "status", "shipment_doc_type", "effective_date"]
    search_fields = ["shipment__shipment_id", "updated_by", "notes"]
    ordering_fields = ["effective_date", "id", "shipment"]


class DriverAdvanceViewSet(BaseOperationsViewSet):
    queryset = DriverAdvance.objects.select_related("driver", "shipment", "content_type").all().order_by("-date", "-id")
    serializer_class = DriverAdvanceSerializer
    filterset_fields = ["driver", "shipment", "is_settled", "date", "content_type", "object_id"]
    search_fields = ["description", "driver__first_name", "driver__last_name", "shipment__shipment_id"]
    ordering_fields = ["date", "amount", "carried_forward", "total_expenses", "id"]

    @action(detail=True, methods=["post"], url_path="settle")
    def settle(self, request, pk=None):
        advance = self.get_object()
        advance.settle_and_carry_forward()
        return Response(self.get_serializer(advance).data)


class DieselViewSet(BaseOperationsViewSet):
    queryset = Diesel.objects.select_related("vehicle", "driver", "location").all().order_by("-date", "-id")
    serializer_class = DieselSerializer
    filterset_fields = ["vehicle", "driver", "payment_mode", "date", "location"]
    search_fields = ["vehicle__registration_number", "driver__first_name", "driver__last_name", "description"]
    ordering_fields = ["date", "quantity", "price_per_ltr", "total_price", "payment", "created_at", "id"]

