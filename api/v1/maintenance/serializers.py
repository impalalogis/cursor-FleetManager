"""
Maintenance API serializers.
"""

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from entity.models import Driver, Organization
from maintenance.models import MaintenanceRecord, Tyre, TyreTransaction


def _parse_combined_reference(value: str):
    if not value:
        return None, None
    if value.startswith("driver_"):
        return "driver", int(value.split("_", 1)[1])
    if value.startswith("owner_"):
        return "organization", int(value.split("_", 1)[1])
    raise serializers.ValidationError("Invalid combined reference format.")


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    vehicle_number = serializers.CharField(source="vehicle.registration_number", read_only=True)
    service_type_display = serializers.CharField(source="service_type.display_value", read_only=True)
    vendors_display = serializers.CharField(source="vendors.display_value", read_only=True)
    performed_by_label = serializers.SerializerMethodField()
    performed_by_combined = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = MaintenanceRecord
        fields = [
            "id",
            "vehicle",
            "vehicle_number",
            "service_type",
            "service_type_display",
            "items",
            "service_date",
            "next_due_date",
            "mileage_at_service",
            "tyre",
            "next_mileage_due_date",
            "invoice_no",
            "vendors",
            "vendors_display",
            "quantity",
            "rate",
            "gst",
            "total_cost",
            "notes",
            "maintenance_document",
            "content_type",
            "object_id",
            "performed_by_combined",
            "performed_by_label",
        ]

    def get_performed_by_label(self, obj):
        if not obj.performed_by:
            return None
        model = obj.content_type.model if obj.content_type else ""
        if model == "organization":
            return f"Owner: {obj.performed_by}"
        return f"{model.capitalize()}: {obj.performed_by}"

    def validate(self, attrs):
        combined = attrs.pop("performed_by_combined", None)
        content_type = attrs.get("content_type", getattr(self.instance, "content_type", None))
        object_id = attrs.get("object_id", getattr(self.instance, "object_id", None))

        if combined:
            model_name, object_id = _parse_combined_reference(combined)
            if model_name == "driver":
                content_type = ContentType.objects.get_for_model(Driver)
                if not Driver.objects.filter(pk=object_id).exists():
                    raise serializers.ValidationError({"performed_by_combined": "Selected driver does not exist."})
            else:
                content_type = ContentType.objects.get_for_model(Organization)
                owner = Organization.objects.filter(pk=object_id).first()
                if not owner or getattr(owner, "organization_type_code", None) != "OWNER":
                    raise serializers.ValidationError({"performed_by_combined": "Selected owner does not exist."})
            attrs["content_type"] = content_type
            attrs["object_id"] = object_id

        if content_type and (content_type.app_label, content_type.model) not in {
            ("entity", "driver"),
            ("entity", "organization"),
        }:
            raise serializers.ValidationError({"content_type": "Must reference entity.driver or entity.organization."})

        if content_type and object_id and content_type.model == "organization":
            owner = content_type.get_object_for_this_type(pk=object_id)
            if getattr(owner, "organization_type_code", None) != "OWNER":
                raise serializers.ValidationError({"object_id": "Organization must be of type OWNER."})

        return attrs


class TyreSerializer(serializers.ModelSerializer):
    brand_display = serializers.CharField(source="brand.display_value", read_only=True)
    model_display = serializers.CharField(source="model.display_value", read_only=True)
    size_display = serializers.CharField(source="size.display_value", read_only=True)
    current_vehicle = serializers.SerializerMethodField()

    class Meta:
        model = Tyre
        fields = [
            "id",
            "tyreNo",
            "tyre_document",
            "brand",
            "brand_display",
            "model",
            "model_display",
            "size",
            "size_display",
            "type",
            "tube_type",
            "ply_rating",
            "purchase_date",
            "purchase_type",
            "purchase_by",
            "amount",
            "invoice_document",
            "created_at",
            "updated_at",
            "current_vehicle",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_current_vehicle(self, obj):
        vehicle = obj.get_current_vehicle()
        return vehicle.registration_number if vehicle else None


class TyreTransactionSerializer(serializers.ModelSerializer):
    tyre_no = serializers.CharField(source="tyre.tyreNo", read_only=True)
    vehicle_number = serializers.CharField(source="vehicle.registration_number", read_only=True)
    transaction_type_display = serializers.CharField(source="transaction_type.display_value", read_only=True)

    class Meta:
        model = TyreTransaction
        fields = [
            "id",
            "tyre",
            "tyre_no",
            "vehicle",
            "vehicle_number",
            "position",
            "transaction_type",
            "transaction_type_display",
            "transaction_date",
            "cost",
            "performed_by",
            "notes",
        ]
