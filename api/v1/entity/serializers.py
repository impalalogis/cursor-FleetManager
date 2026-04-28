"""
Entity API serializers.
"""

from rest_framework import serializers

from entity.models import Driver, DriverDocument, Organization, OrganizationDocument, Vehicle, VehicleDocument


class OrganizationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationDocument
        fields = "__all__"


class DriverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverDocument
        fields = "__all__"


class VehicleDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleDocument
        fields = "__all__"


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "__all__"

    def validate_owner(self, owner):
        if owner and getattr(owner, "organization_type_code", None) != "OWNER":
            raise serializers.ValidationError("Selected organization must be of type OWNER.")
        return owner


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = "__all__"
