"""
Entity API viewsets and domain actions.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response

from api.utils import BulkModelViewSet, StandardResultsSetPagination
from entity.models import Driver, DriverDocument, Organization, OrganizationDocument, Vehicle, VehicleDocument
from maintenance.models import MaintenanceRecord, TyreTransaction

from .serializers import (
    DriverDocumentSerializer,
    DriverSerializer,
    OrganizationDocumentSerializer,
    OrganizationSerializer,
    VehicleDocumentSerializer,
    VehicleSerializer,
)


class BaseEntityViewSet(BulkModelViewSet):
    authentication_classes = []
    permission_classes = []
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class OrganizationDocumentViewSet(BaseEntityViewSet):
    queryset = OrganizationDocument.objects.select_related("organization", "doc_type").all().order_by("-uploaded_at")
    serializer_class = OrganizationDocumentSerializer
    filterset_fields = ["organization", "doc_type", "issue_date", "expiry_date"]
    search_fields = ["organization__organization_name", "doc_no", "doc_type__display_value", "notes"]
    ordering_fields = ["uploaded_at", "expiry_date", "issue_date", "id"]


class DriverDocumentViewSet(BaseEntityViewSet):
    queryset = DriverDocument.objects.select_related("driver", "doc_type").all().order_by("-uploaded_at")
    serializer_class = DriverDocumentSerializer
    filterset_fields = ["driver", "doc_type", "issue_date", "expiry_date"]
    search_fields = ["driver__first_name", "driver__last_name", "doc_no", "doc_type__display_value"]
    ordering_fields = ["uploaded_at", "expiry_date", "issue_date", "id"]


class VehicleDocumentViewSet(BaseEntityViewSet):
    queryset = VehicleDocument.objects.select_related("vehicle", "doc_type").all().order_by("-uploaded_at")
    serializer_class = VehicleDocumentSerializer
    filterset_fields = ["vehicle", "doc_type", "issue_date", "expiry_date"]
    search_fields = ["vehicle__registration_number", "doc_type__display_value", "notes"]
    ordering_fields = ["uploaded_at", "expiry_date", "issue_date", "id"]


class OrganizationViewSet(BaseEntityViewSet):
    serializer_class = OrganizationSerializer
    filterset_fields = ["organization_type", "location", "city", "state"]
    search_fields = ["organization_name", "organization_number", "GST_NO", "contact_person", "phone_number", "email"]
    ordering_fields = ["organization_name", "organization_number", "created_at", "updated_at", "id"]

    def get_queryset(self):
        return Organization._base_manager.select_related("organization_type", "location").all().order_by("organization_name")

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        queryset = OrganizationDocument.objects.filter(organization_id=pk).select_related("doc_type").order_by("-uploaded_at")
        page = self.paginate_queryset(queryset)
        serializer = OrganizationDocumentSerializer(page, many=True) if page is not None else OrganizationDocumentSerializer(queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="drivers")
    def drivers(self, request, pk=None):
        queryset = Driver.objects.filter(owner_id=pk).order_by("first_name", "last_name")
        page = self.paginate_queryset(queryset)
        serializer = DriverSerializer(page, many=True) if page is not None else DriverSerializer(queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class DriverViewSet(BaseEntityViewSet):
    queryset = Driver.objects.select_related("owner").all().order_by("first_name", "last_name")
    serializer_class = DriverSerializer
    filterset_fields = ["owner", "gender", "is_active", "city", "state"]
    search_fields = [
        "first_name",
        "middle_name",
        "last_name",
        "license_number",
        "phone_number",
        "contact_phone",
        "contact_email",
    ]
    ordering_fields = ["first_name", "last_name", "date_of_birth", "created_at", "updated_at", "id"]

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        queryset = DriverDocument.objects.filter(driver_id=pk).select_related("doc_type").order_by("-uploaded_at")
        page = self.paginate_queryset(queryset)
        serializer = DriverDocumentSerializer(page, many=True) if page is not None else DriverDocumentSerializer(queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="advance-summary")
    def advance_summary(self, request, pk=None):
        driver = self.get_object()
        return Response(driver.driver_advance_summary())

    @action(detail=True, methods=["get"], url_path="current-vehicle")
    def current_vehicle(self, request, pk=None):
        driver = self.get_object()
        vehicle = driver.current_vehicle
        if not vehicle:
            return Response({"detail": "No current vehicle found.", "current_vehicle": None})
        return Response(VehicleSerializer(vehicle).data)


class VehicleViewSet(BaseEntityViewSet):
    queryset = Vehicle.objects.select_related(
        "owner",
        "brand_name",
        "model_name",
        "truck_type",
        "engine_type",
        "fuel_type",
        "body_type",
        "truck_specification",
        "wheel_count",
        "load_capacity_tons",
        "state_registered",
    ).all().order_by("registration_number")
    serializer_class = VehicleSerializer
    filterset_fields = ["owner", "brand_name", "model_name", "truck_type", "fuel_type", "is_active", "state_registered"]
    search_fields = ["registration_number", "chassis_number", "owner__organization_name", "brand_name__display_value", "model_name__display_value"]
    ordering_fields = ["registration_number", "created_at", "updated_at", "maintenance_due_date", "id"]

    @action(detail=True, methods=["get"], url_path="documents")
    def documents(self, request, pk=None):
        queryset = VehicleDocument.objects.filter(vehicle_id=pk).select_related("doc_type").order_by("-uploaded_at")
        page = self.paginate_queryset(queryset)
        serializer = VehicleDocumentSerializer(page, many=True) if page is not None else VehicleDocumentSerializer(queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="maintenance")
    def maintenance(self, request, pk=None):
        queryset = MaintenanceRecord.objects.filter(vehicle_id=pk).order_by("-service_date", "-id")
        data = [
            {
                "id": row.id,
                "service_date": row.service_date,
                "service_type": row.service_type_id,
                "service_type_label": getattr(row.service_type, "display_value", None) if row.service_type else None,
                "invoice_no": row.invoice_no,
                "total_cost": row.total_cost,
                "next_due_date": row.next_due_date,
                "notes": row.notes,
            }
            for row in queryset.select_related("service_type")
        ]
        return Response(data)

    @action(detail=True, methods=["get"], url_path="tyres")
    def tyres(self, request, pk=None):
        tx_qs = TyreTransaction.objects.filter(vehicle_id=pk).select_related("tyre", "position", "transaction_type").order_by(
            "-transaction_date",
            "-id",
        )
        data = [
            {
                "transaction_id": tx.id,
                "tyre_id": tx.tyre_id,
                "tyre_no": tx.tyre.tyreNo if tx.tyre else None,
                "transaction_date": tx.transaction_date,
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
        return Response(data)
