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

class BankingDetailSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(source="get_account_type_display", read_only=True)
    # banking_status_display = serializers.CharField(source="get_banking_status_display", read_only=True)
    # verification_status_display = serializers.CharField(
    #     source="get_verification_status_display",
    #     read_only=True,
    # )

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankingDetail
        fields = [
            "id",
            "account_holder_name",
            "account_number",
            "bank_name",
            "branch_name",
            "ifsc_code",
            "account_type",
            "account_type_display",
            # "banking_status",
            # "banking_status_display",
            # "verification_status",
            # # "verification_status_display",
            # "is_primary",
            # # "is_verified",
            # "created_at",
            # "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
