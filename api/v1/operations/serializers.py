"""
Operations API serializers.
"""

from rest_framework import serializers

from operations.models import Consignment, ConsignmentGroup, Diesel, DriverAdvance, Shipment, ShipmentExpense, ShipmentStatus


class ConsignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consignment
        fields = "__all__"

    def validate(self, attrs):
        consignor = attrs.get("consignor", getattr(self.instance, "consignor", None))
        consignee = attrs.get("consignee", getattr(self.instance, "consignee", None))
        if consignor and consignee and consignor == consignee:
            raise serializers.ValidationError("Consignor and consignee organizations cannot be the same.")
        return attrs


class ConsignmentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsignmentGroup
        fields = "__all__"


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = "__all__"

    def validate(self, attrs):
        odometer_start = attrs.get("odometer_start", getattr(self.instance, "odometer_start", None))
        odometer_end = attrs.get("odometer_end", getattr(self.instance, "odometer_end", None))
        if odometer_start is not None and odometer_end is not None and odometer_end < odometer_start:
            raise serializers.ValidationError({"odometer_end": "Ending reading must be >= starting reading."})
        return attrs


class ShipmentExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentExpense
        fields = "__all__"


class ShipmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentStatus
        fields = "__all__"


class DriverAdvanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverAdvance
        fields = "__all__"


class DieselSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diesel
        fields = "__all__"

