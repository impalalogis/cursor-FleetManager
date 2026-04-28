"""
Maintenance API viewsets and domain actions.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response

from api.utils import BulkModelViewSet, StandardResultsSetPagination
from maintenance.models import MaintenanceRecord, Tyre, TyreTransaction

from .serializers import MaintenanceRecordSerializer, TyreSerializer, TyreTransactionSerializer


class BaseMaintenanceViewSet(BulkModelViewSet):
    authentication_classes = []
    permission_classes = []
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class MaintenanceRecordViewSet(BaseMaintenanceViewSet):
    queryset = MaintenanceRecord.objects.select_related(
        "vehicle",
        "service_type",
        "items",
        "tyre",
        "vendors",
        "content_type",
    ).all().order_by("-service_date", "-id")
    serializer_class = MaintenanceRecordSerializer
    filterset_fields = [
        "vehicle",
        "service_type",
        "items",
        "tyre",
        "vendors",
        "service_date",
        "next_due_date",
        "content_type",
        "object_id",
    ]
    search_fields = [
        "vehicle__registration_number",
        "invoice_no",
        "notes",
        "service_type__display_value",
        "vendors__display_value",
    ]
    ordering_fields = ["service_date", "next_due_date", "total_cost", "id"]

    @action(detail=True, methods=["get"], url_path="validate")
    def validate_record(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=self.get_serializer(instance).data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response({"valid": True, "id": instance.id})


class TyreViewSet(BaseMaintenanceViewSet):
    queryset = Tyre.objects.select_related("brand", "model", "size", "type", "tube_type", "purchase_type").all().order_by(
        "-purchase_date",
        "-id",
    )
    serializer_class = TyreSerializer
    filterset_fields = ["brand", "model", "size", "type", "tube_type", "purchase_type", "purchase_date"]
    search_fields = ["tyreNo", "brand__display_value", "model__display_value", "purchase_by"]
    ordering_fields = ["purchase_date", "amount", "created_at", "updated_at", "id"]

    @action(detail=True, methods=["get"], url_path="current-vehicle")
    def current_vehicle(self, request, pk=None):
        tyre = self.get_object()
        vehicle = tyre.get_current_vehicle()
        if not vehicle:
            return Response({"current_vehicle": None, "detail": "Tyre not currently installed."})
        return Response(
            {
                "id": str(vehicle.id),
                "registration_number": vehicle.registration_number,
                "owner_id": vehicle.owner_id,
            }
        )

    @action(detail=True, methods=["get"], url_path="lifecycle")
    def lifecycle(self, request, pk=None):
        tyre = self.get_object()
        tx_qs = tyre.transactions.select_related("vehicle", "position", "transaction_type").order_by("transaction_date", "id")
        timeline = [
            {
                "id": tx.id,
                "transaction_date": tx.transaction_date,
                "vehicle_id": str(tx.vehicle_id),
                "vehicle_registration": tx.vehicle.registration_number if tx.vehicle else None,
                "position_id": tx.position_id,
                "position_label": tx.position.display_value if tx.position else None,
                "transaction_type_id": tx.transaction_type_id,
                "transaction_type_label": tx.transaction_type.display_value if tx.transaction_type else None,
                "cost": tx.cost,
                "performed_by": tx.performed_by,
                "notes": tx.notes,
            }
            for tx in tx_qs
        ]
        return Response(
            {
                "tyre_id": tyre.id,
                "tyre_no": tyre.tyreNo,
                "age": tyre.age,
                "current_vehicle": tyre.get_current_vehicle().registration_number if tyre.get_current_vehicle() else None,
                "transactions": timeline,
            }
        )


class TyreTransactionViewSet(BaseMaintenanceViewSet):
    queryset = TyreTransaction.objects.select_related("tyre", "vehicle", "position", "transaction_type").all().order_by(
        "-transaction_date",
        "-id",
    )
    serializer_class = TyreTransactionSerializer
    filterset_fields = ["tyre", "vehicle", "position", "transaction_type", "transaction_date"]
    search_fields = ["tyre__tyreNo", "vehicle__registration_number", "performed_by", "notes"]
    ordering_fields = ["transaction_date", "cost", "id"]

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        row = self.get_object()
        tx_qs = TyreTransaction.objects.filter(tyre=row.tyre).select_related(
            "vehicle",
            "position",
            "transaction_type",
        ).order_by("-transaction_date", "-id")
        data = [
            {
                "id": tx.id,
                "transaction_date": tx.transaction_date,
                "vehicle_registration": tx.vehicle.registration_number if tx.vehicle else None,
                "position_label": tx.position.display_value if tx.position else None,
                "transaction_type_label": tx.transaction_type.display_value if tx.transaction_type else None,
                "cost": tx.cost,
                "performed_by": tx.performed_by,
                "notes": tx.notes,
            }
            for tx in tx_qs
        ]
        return Response({"tyre_id": row.tyre_id, "history": data})

