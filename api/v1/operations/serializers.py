"""
Operations Serializers for Fleet Manager API
Comprehensive serializers matching admin panel functionality
"""

from rest_framework import serializers
from operations.models import (
    ConsignmentGroup, Consignment, Shipment, ShipmentExpense, 
    DriverAdvance, ShipmentStatus
)
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist

class ConsignmentSerializer(serializers.ModelSerializer):
    # Read-only / auto fields
    id = serializers.IntegerField(read_only=True)
    consignment_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    # Optional: human labels for foreign keys (read-only)
    consignor_label = serializers.StringRelatedField(source="consignor", read_only=True)
    consignee_label = serializers.StringRelatedField(source="consignee", read_only=True)
    freight_mode_label = serializers.StringRelatedField(source="freight_mode", read_only=True)
    material_type_label = serializers.StringRelatedField(source="material_type", read_only=True)
    weight_unit_label = serializers.StringRelatedField(source="weight_unit", read_only=True)
    packaging_type_label = serializers.StringRelatedField(source="packaging_type", read_only=True)
    vehicle_type_label = serializers.StringRelatedField(source="vehicle_type", read_only=True)

    class Meta:
        model = Consignment
        fields = [
            # ids
            "id", "consignment_id",

            # parties
            "consignor", "consignee",

            # goods & measures
            "material_type",
            "weight", "weight_unit", "volume",
            "number_of_packages", "packaging_type",
            "vehicle_type",

            # pricing
            "freight_mode", "rate", "total_freight",

            # schedule
            "schedule_date", "scheduled_pickup_time",
            "expected_delivery_date", "expected_delivery_time",

            # meta
            "created_at", "updated_at", "created_by",

            # labels
            "consignor_label", "consignee_label",
            "freight_mode_label", "material_type_label", "weight_unit_label",
            "packaging_type_label", "vehicle_type_label",
        ]

    def validate(self, attrs):
        """
        Mirror the model.clean() logic here so API returns neat 400s.
        """
        consignor = attrs.get("consignor", getattr(self.instance, "consignor", None))
        consignee = attrs.get("consignee", getattr(self.instance, "consignee", None))

        if consignor is not None and consignee is not None and consignor == consignee:
            raise serializers.ValidationError("Consignor and consignee organizations cannot be the same.")

        # Positive weight guard (DB has a check too)
        weight = attrs.get("weight", getattr(self.instance, "weight", None))
        if weight is not None and Decimal(weight) <= 0:
            raise serializers.ValidationError({"weight": "Weight must be greater than 0."})

        # Freight-mode dependent rules (your Choice likely has an internal_value or code)
        # We'll check common fields that might exist; fall back to its string if needed.
        fm = attrs.get("freight_mode", getattr(self.instance, "freight_mode", None))
        rate = attrs.get("rate", getattr(self.instance, "rate", None))

        def get_mode_value(choice_obj):
            # Try internal_value, else value, else name/str
            for attr in ("internal_value", "value", "code"):
                if choice_obj is not None and hasattr(choice_obj, attr):
                    return getattr(choice_obj, attr)
            return str(choice_obj) if choice_obj is not None else None

        mode_val = get_mode_value(fm)
        if mode_val:
            if str(mode_val).lower() == "rate":
                if not rate:
                    raise serializers.ValidationError({"rate": "Rate per unit is required when freight mode is 'Rate'."})
            # Example for "Fixed" mode: rate must be present as total amount
            if str(mode_val).lower() == "fixed" and not rate:
                raise serializers.ValidationError({"rate": "Rate (fixed amount) is required when freight mode is 'Fixed'."})

        # number_of_packages positive (DB also has check)
        nop = attrs.get("number_of_packages", getattr(self.instance, "number_of_packages", None))
        if nop is not None and nop <= 0:
            raise serializers.ValidationError({"number_of_packages": "Must be greater than 0 (or omit/null)."})

        return attrs

class ConsignmentGroupSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    group_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    # Accept list of consignment IDs for M2M
    consignments = serializers.PrimaryKeyRelatedField(
        queryset=Consignment.objects.all(),
        many=True,
        required=False
    )

    # Read-only helpers
    consignment_count = serializers.SerializerMethodField()
    route_summary = serializers.SerializerMethodField()

    class Meta:
        model = ConsignmentGroup
        fields = [
            "id", "group_id",
            "consignments",
            "planned_dispatch_date", "actual_dispatch_date",
            "total_weight", "total_amount",
            "created_at", "updated_at", "created_by",
            # computed
            "consignment_count", "route_summary",
        ]

    def get_consignment_count(self, obj):
        try:
            return obj.get_consignment_count()
        except Exception:
            return 0

    def get_route_summary(self, obj):
        try:
            return obj.get_route_summary()
        except Exception:
            return []

    def create(self, validated_data):
        consignments = validated_data.pop("consignments", [])
        obj = ConsignmentGroup.objects.create(**validated_data)
        if consignments:
            obj.consignments.set(consignments)
            obj.calculate_totals()
        return obj

    def update(self, instance, validated_data):
        consignments = validated_data.pop("consignments", None)
        # assign simple fields
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # update M2M only if provided
        if consignments is not None:
            instance.consignments.set(consignments)
            instance.calculate_totals()
        else:
            # if totals depend on dates only, skip; otherwise keep totals as-is
            pass
        return instance




ALLOWED_CT = {
    ("entity", "driver"),
    ("entity", "organization"),
}

class ShipmentExpenseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    # Read-only convenience labels
    shipment_label = serializers.StringRelatedField(source="shipment", read_only=True)
    expense_by_label = serializers.SerializerMethodField()
    expense_type_label = serializers.StringRelatedField(source="expense_type", read_only=True)

    class Meta:
        model = ShipmentExpense
        fields = [
            "id",
            "shipment", "shipment_label",

      # Generic relation (expense_by = Driver/Owner organization)
            "content_type", "object_id", "expense_by_label",

            # What/when/how much
            "expense_type", "expense_type_label",
            "amount", "expense_date", "description",

            # Optional file
            "shipment_expense_document",
        ]

    def get_expense_by_label(self, obj):
        try:
            return str(obj.expense_by) if obj.expense_by else None
        except Exception:
            return None

    def validate(self, attrs):
        """
        Ensure expense_by points to entity.Driver or an OWNER organization and object exists.
        """
        ct = attrs.get("content_type", getattr(self.instance, "content_type", None))
        oid = attrs.get("object_id", getattr(self.instance, "object_id", None))

        if ct and (ct.app_label, ct.model) not in ALLOWED_CT:
            raise serializers.ValidationError({"content_type": "Must reference entity.driver or an OWNER organization."})

        if ct and oid:
            try:
                target = ct.get_object_for_this_type(pk=oid)
            except ObjectDoesNotExist:
                raise serializers.ValidationError({"object_id": "Target object does not exist."})
            else:
                if ct.model == 'organization' and getattr(target, 'organization_type_code', None) != 'OWNER':
                    raise serializers.ValidationError({"object_id": "Organization must have type OWNER."})

        # amount non-negative
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if amount is not None and amount < 0:
            raise serializers.ValidationError({"amount": "Amount must be ≥ 0."})

        return attrs


# api/v1/entity/serializers.py
class DriverAdvanceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    # computed helpers
    remaining_balance = serializers.SerializerMethodField()
    advance_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = DriverAdvance
        fields = [
            "id",
            "driver",
            "shipment",
            "description",
            "date",
            "amount",
            "total_expenses",
            "is_settled",
            "carried_forward",
            # computed
            "remaining_balance",
            "advance_breakdown",
        ]
        read_only_fields = ["total_expenses", "carried_forward", "is_settled"]

    def get_remaining_balance(self, obj):
        try:
            return obj.remaining_balance()
        except Exception:
            return None

    def get_advance_breakdown(self, obj):
        try:
            return obj.advance_breakdown()
        except Exception:
            return None

    def validate(self, attrs):
        amt = attrs.get("amount", getattr(self.instance, "amount", 0))
        if amt is not None and amt < 0:
            raise serializers.ValidationError({"amount": "Amount must be ≥ 0."})
        return attrs


class ShipmentStatusSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)

    # Read-only convenience labels
    shipment_label = serializers.StringRelatedField(source="shipment", read_only=True)
    status_label = serializers.StringRelatedField(source="status", read_only=True)
    shipment_doc_type_label = serializers.StringRelatedField(source="shipment_doc_type", read_only=True)

    class Meta:
        model = ShipmentStatus
        fields = [
            "id",
            "shipment", "shipment_label",
            "status", "status_label",
            "shipment_doc_type", "shipment_doc_type_label",
            "shipment_document",
            "timestamp",
            "updated_by",
            "notes",
        ]

    def validate(self, attrs):
        return attrs


class ShipmentSerializer(serializers.ModelSerializer):
    # Read-only / auto
    id = serializers.IntegerField(read_only=True)
    shipment_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    total_distance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    total_freight_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, allow_null=True)

    # Convenience labels (read-only)
    consignment_group_label = serializers.StringRelatedField(source="consignment_group", read_only=True)
    vehicle_label = serializers.StringRelatedField(source="vehicle", read_only=True)
    driver_label = serializers.StringRelatedField(source="driver", read_only=True)
    co_driver_label = serializers.StringRelatedField(source="co_driver", read_only=True)
    transporter_label = serializers.StringRelatedField(source="transporter", read_only=True)
    broker_label = serializers.StringRelatedField(source="broker", read_only=True)
    planned_route_label = serializers.StringRelatedField(source="planned_route", read_only=True)
    actual_route_label = serializers.StringRelatedField(source="actual_route", read_only=True)

    # Computed helpers
    consignment_count = serializers.SerializerMethodField()
    route_summary = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = [
            "id", "shipment_id",
            # links
            "consignment_group", "consignment_group_label",
            "vehicle", "vehicle_label",
            "driver", "driver_label",
            "co_driver", "co_driver_label",
            "transporter", "transporter_label",
            "broker", "broker_label",
            # timing
            "planned_departure", "actual_departure",
            "planned_arrival", "actual_arrival",
            # odo / distance
            "odometer_start", "odometer_end", "total_distance",
            # money
            "freight_advance", "total_freight_amount",
            # misc
            "notes",
            "planned_route", "planned_route_label",
            "actual_route", "actual_route_label",
            # meta
            "created_at", "updated_at", "created_by",
            # computed
            "consignment_count", "route_summary",
        ]

    def get_consignment_count(self, obj):
        try:
            return obj.get_consignment_count()
        except Exception:
            return 0

    def get_route_summary(self, obj):
        try:
            return obj.get_route_summary()
        except Exception:
            return []

    def validate(self, attrs):
        """
        Lightweight API-side checks so you get a neat 400 instead of DB errors.
        Model-level CheckConstraints will still enforce at DB.
        """
        odometer_start = attrs.get("odometer_start", getattr(self.instance, "odometer_start", None))
        odometer_end = attrs.get("odometer_end", getattr(self.instance, "odometer_end", None))
        if odometer_start is not None and odometer_end is not None and odometer_end < odometer_start:
            raise serializers.ValidationError({"odometer_end": "Ending reading must be >= starting reading."})

        adv = attrs.get("freight_advance", getattr(self.instance, "freight_advance", 0))
        if adv is not None and adv < 0:
            raise serializers.ValidationError({"freight_advance": "Advance must be >= 0."})
        return attrs

class ShipmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Shipment list view"""
    consignment_group_id = serializers.CharField(source='consignment_group.group_id', read_only=True)
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    vehicle_number = serializers.CharField(source='vehicle.registration_number', read_only=True)
    
    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_id', 'consignment_group_id', 'driver_name',
            'vehicle_number', 'dispatch_date', 'expected_delivery_date',
            'current_status', 'freight_amount'
        ]