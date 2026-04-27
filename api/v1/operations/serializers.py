"""
Operations API serializers.
"""

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

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


def _parse_combined_reference(value: str):
    """
    Parse values like 'driver_12' / 'owner_45'.
    """
    if not value:
        return None, None
    if value.startswith("driver_"):
        return "driver", int(value.split("_", 1)[1])
    if value.startswith("owner_"):
        return "organization", int(value.split("_", 1)[1])
    raise serializers.ValidationError("Invalid combined reference format.")


class ConsignmentSerializer(serializers.ModelSerializer):
    consignment_id = serializers.CharField(read_only=True)

    class Meta:
        model = Consignment
        fields = [
            "id",
            "consignment_id",
            "consignor",
            "consignee",
            "from_location",
            "to_location",
            "material_type",
            "weight",
            "weight_unit",
            "volume",
            "number_of_packages",
            "packaging_type",
            "vehicle_type",
            "freight_mode",
            "rate",
            "total_freight",
            "schedule_date",
            "scheduled_pickup_time",
            "expected_delivery_date",
            "expected_delivery_time",
            "created_at",
            "updated_at",
            "created_by",
        ]
        read_only_fields = ["total_freight", "created_at", "updated_at", "created_by"]

    def validate(self, attrs):
        consignor = attrs.get("consignor", getattr(self.instance, "consignor", None))
        consignee = attrs.get("consignee", getattr(self.instance, "consignee", None))
        if consignor and consignee and consignor == consignee:
            raise serializers.ValidationError("Consignor and consignee organizations cannot be the same.")

        weight = attrs.get("weight", getattr(self.instance, "weight", None))
        if weight is not None and Decimal(str(weight)) <= 0:
            raise serializers.ValidationError({"weight": "Weight must be greater than 0."})
        return attrs


class ConsignmentGroupSerializer(serializers.ModelSerializer):
    group_id = serializers.CharField(read_only=True)
    consignments = serializers.PrimaryKeyRelatedField(
        queryset=Consignment.objects.all(),
        many=True,
        required=False,
    )
    consignment_count = serializers.SerializerMethodField()
    route_summary = serializers.SerializerMethodField()

    class Meta:
        model = ConsignmentGroup
        fields = [
            "id",
            "group_id",
            "consignments",
            "planned_dispatch_date",
            "actual_dispatch_date",
            "total_weight",
            "total_amount",
            "created_at",
            "updated_at",
            "created_by",
            "consignment_count",
            "route_summary",
        ]
        read_only_fields = ["total_weight", "total_amount", "created_at", "updated_at", "created_by"]

    def get_consignment_count(self, obj):
        return obj.get_consignment_count()

    def get_route_summary(self, obj):
        return obj.get_route_summary()

    def create(self, validated_data):
        consignments = validated_data.pop("consignments", [])
        instance = ConsignmentGroup.objects.create(**validated_data)
        if consignments:
            instance.consignments.set(consignments)
            instance.calculate_totals()
        return instance

    def update(self, instance, validated_data):
        consignments = validated_data.pop("consignments", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if consignments is not None:
            instance.consignments.set(consignments)
            instance.calculate_totals()
        return instance


class ShipmentSerializer(serializers.ModelSerializer):
    shipment_id = serializers.CharField(read_only=True)
    total_distance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    total_freight_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, allow_null=True)
    consignment_count = serializers.SerializerMethodField()
    route_summary = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "id",
            "shipment_id",
            "consignment_group",
            "e_way_bill",
            "invoice_no",
            "vehicle",
            "driver",
            "co_driver",
            "transporter",
            "broker",
            "planned_departure",
            "actual_departure",
            "planned_arrival",
            "actual_arrival",
            "odometer_start",
            "odometer_end",
            "total_distance",
            "freight_advance",
            "total_freight_amount",
            "notes",
            "planned_route",
            "actual_route",
            "lr_no",
            "created_at",
            "updated_at",
            "created_by",
            "consignment_count",
            "route_summary",
        ]
        read_only_fields = [
            "shipment_id",
            "total_distance",
            "total_freight_amount",
            "created_at",
            "updated_at",
            "created_by",
        ]

    def get_consignment_count(self, obj):
        return obj.get_consignment_count()

    def get_route_summary(self, obj):
        return obj.get_route_summary()

    def validate(self, attrs):
        odometer_start = attrs.get("odometer_start", getattr(self.instance, "odometer_start", None))
        odometer_end = attrs.get("odometer_end", getattr(self.instance, "odometer_end", None))
        if odometer_start is not None and odometer_end is not None and odometer_end < odometer_start:
            raise serializers.ValidationError({"odometer_end": "Ending reading must be >= starting reading."})
        return attrs


class ShipmentExpenseSerializer(serializers.ModelSerializer):
    expense_by_label = serializers.SerializerMethodField()
    expense_by_combined = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ShipmentExpense
        fields = [
            "id",
            "shipment",
            "content_type",
            "object_id",
            "expense_by_combined",
            "expense_by_label",
            "expense_type",
            "amount",
            "expense_date",
            "description",
            "shipment_expense_document",
        ]

    def get_expense_by_label(self, obj):
        return str(obj.expense_by) if obj.expense_by else None

    def validate(self, attrs):
        combined = attrs.pop("expense_by_combined", None)
        content_type = attrs.get("content_type", getattr(self.instance, "content_type", None))
        object_id = attrs.get("object_id", getattr(self.instance, "object_id", None))

        if combined:
            model_name, object_id = _parse_combined_reference(combined)
            if model_name == "driver":
                content_type = ContentType.objects.get_for_model(Driver)
                if not Driver.objects.filter(pk=object_id).exists():
                    raise serializers.ValidationError({"expense_by_combined": "Selected driver does not exist."})
            else:
                content_type = ContentType.objects.get_for_model(Organization)
                owner = Organization.objects.filter(pk=object_id).first()
                if not owner or getattr(owner, "organization_type_code", None) != "OWNER":
                    raise serializers.ValidationError({"expense_by_combined": "Selected owner does not exist."})
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

        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if amount is not None and amount < 0:
            raise serializers.ValidationError({"amount": "Amount must be >= 0."})
        return attrs


class ShipmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentStatus
        fields = [
            "id",
            "shipment",
            "status",
            "shipment_doc_type",
            "shipment_document",
            "effective_date",
            "updated_by",
            "notes",
        ]


class DriverAdvanceSerializer(serializers.ModelSerializer):
    remaining_balance = serializers.SerializerMethodField()
    advance_breakdown = serializers.SerializerMethodField()
    advance_by_label = serializers.SerializerMethodField()
    related_type = serializers.ChoiceField(
        choices=["owner", "shipment"],
        required=False,
        write_only=True,
    )
    owner_ref = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = DriverAdvance
        fields = [
            "id",
            "driver",
            "shipment",
            "content_type",
            "object_id",
            "related_type",
            "owner_ref",
            "advance_by_label",
            "description",
            "date",
            "amount",
            "total_expenses",
            "is_settled",
            "carried_forward",
            "remaining_balance",
            "advance_breakdown",
        ]
        read_only_fields = ["total_expenses", "is_settled", "carried_forward"]

    def get_remaining_balance(self, obj):
        return obj.remaining_balance()

    def get_advance_breakdown(self, obj):
        return obj.advance_breakdown()

    def get_advance_by_label(self, obj):
        return str(obj.advance_by) if obj.advance_by else None

    def validate(self, attrs):
        related_type = attrs.pop("related_type", None)
        owner_ref = attrs.pop("owner_ref", None)

        if related_type == "owner":
            owner = Organization.objects.filter(pk=owner_ref).first() if owner_ref else None
            if not owner or getattr(owner, "organization_type_code", None) != "OWNER":
                raise serializers.ValidationError({"owner_ref": "Valid OWNER organization is required."})
            attrs["content_type"] = ContentType.objects.get_for_model(Organization)
            attrs["object_id"] = owner.pk
        elif related_type == "shipment":
            shipment = attrs.get("shipment", getattr(self.instance, "shipment", None))
            if not shipment:
                raise serializers.ValidationError({"shipment": "Shipment is required when related_type=shipment."})
            attrs["content_type"] = ContentType.objects.get_for_model(Shipment)
            attrs["object_id"] = shipment.pk

        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if amount is not None and amount < 0:
            raise serializers.ValidationError({"amount": "Amount must be >= 0."})
        return attrs


class DieselSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diesel
        fields = [
            "id",
            "vehicle",
            "driver",
            "date",
            "description",
            "price_per_ltr",
            "quantity",
            "total_price",
            "full_km",
            "mileage",
            "rs_per_km",
            "payment",
            "payment_mode",
            "location",
            "driver_taken_cash",
            "upload_doc",
            "created_at",
        ]
        read_only_fields = ["total_price", "mileage", "rs_per_km", "payment", "created_at"]
