"""
Entity API serializers.
"""

from rest_framework import serializers

from configuration.models import BankingDetail, Choice, Location, Route
from entity.models import (
    Driver,
    DriverDocument,
    Organization,
    OrganizationDocument,
    Vehicle,
    VehicleDocument,
)


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "category", "display_value", "internal_value"]


class OrganizationSerializer(serializers.ModelSerializer):
    organization_number = serializers.CharField(read_only=True)
    organization_type_label = serializers.CharField(
        source="organization_type.display_value",
        read_only=True,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "organization_number",
            "organization_name",
            "organization_type",
            "organization_type_label",
            "location",
            "notes",
            "address_line_1",
            "address_line_2",
            "locality",
            "city",
            "district",
            "state",
            "country",
            "pincode",
            "landmark",
            "contact_person",
            "contact_phone",
            "contact_email",
            "phone_number",
            "email",
            "GST_NO",
            "GST_document",
            "pan_number",
            "pan_document",
            "tds_declaration",
        ]


class VehicleSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.organization_name", read_only=True)
    maintenance_due = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "registration_number",
            "chassis_number",
            "brand_name",
            "model_name",
            "truck_type",
            "engine_type",
            "fuel_type",
            "body_type",
            "truck_specification",
            "wheel_count",
            "load_capacity_tons",
            "maintenance_due_date",
            "insurance_expiry",
            "fitness_certificate_expiry",
            "pollution_certificate_expiry",
            "owner",
            "owner_name",
            "state_registered",
            "is_active",
            "maintenance_due",
        ]

    def get_maintenance_due(self, obj):
        return bool(getattr(obj, "is_maintenance_due", False))


class DriverSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    license_status = serializers.CharField(read_only=True)
    current_vehicle_id = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.organization_name", read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "title",
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "gender",
            "contact_person",
            "contact_phone",
            "contact_email",
            "phone_number",
            "email",
            "address_line_1",
            "address_line_2",
            "locality",
            "city",
            "district",
            "state",
            "country",
            "pincode",
            "landmark",
            "owner",
            "owner_name",
            "license_number",
            "license_document",
            "license_expiry",
            "family_name",
            "family_address_line_1",
            "family_address_line_2",
            "family_locality",
            "family_city",
            "family_district",
            "family_state",
            "family_country",
            "family_pincode",
            "family_landmark",
            "family_phone_number",
            "is_active",
            "age",
            "full_name",
            "license_status",
            "current_vehicle_id",
        ]

    def get_current_vehicle_id(self, obj):
        vehicle = getattr(obj, "current_vehicle", None)
        return str(vehicle.id) if vehicle else None

    def validate(self, attrs):
        owner = attrs.get("owner", getattr(self.instance, "owner", None))
        if owner is None:
            raise serializers.ValidationError(
                {"owner": "This field is required (driver must belong to an owner organization)."}
            )
        if getattr(owner, "organization_type_code", None) != "OWNER":
            raise serializers.ValidationError({"owner": "Selected organization must be of type OWNER."})
        return attrs


class _BaseDocumentSerializer(serializers.ModelSerializer):
    doc_type_label = serializers.CharField(source="doc_type.display_value", read_only=True)
    file_url = serializers.SerializerMethodField()

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not getattr(obj, "file", None):
            return None
        if request is None:
            return obj.file.url
        return request.build_absolute_uri(obj.file.url)


class DriverDocumentSerializer(_BaseDocumentSerializer):
    driver_name = serializers.CharField(source="driver.full_name", read_only=True)

    class Meta:
        model = DriverDocument
        fields = [
            "id",
            "driver",
            "driver_name",
            "doc_type",
            "doc_type_label",
            "doc_no",
            "issue_date",
            "expiry_date",
            "file",
            "file_url",
            "uploaded_at",
        ]
        read_only_fields = ["uploaded_at"]


class OrganizationDocumentSerializer(_BaseDocumentSerializer):
    organization_name = serializers.CharField(source="organization.organization_name", read_only=True)

    class Meta:
        model = OrganizationDocument
        fields = [
            "id",
            "organization",
            "organization_name",
            "doc_type",
            "doc_type_label",
            "doc_no",
            "issue_date",
            "expiry_date",
            "notes",
            "file",
            "file_url",
            "uploaded_at",
        ]
        read_only_fields = ["uploaded_at"]


class VehicleDocumentSerializer(_BaseDocumentSerializer):
    vehicle_registration = serializers.CharField(source="vehicle.registration_number", read_only=True)

    class Meta:
        model = VehicleDocument
        fields = [
            "id",
            "vehicle",
            "vehicle_registration",
            "doc_type",
            "doc_type_label",
            "issue_date",
            "expiry_date",
            "notes",
            "file",
            "file_url",
            "uploaded_at",
        ]
        read_only_fields = ["uploaded_at"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name"]


class RouteSerializer(serializers.ModelSerializer):
    route_display = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ["id", "source", "via", "destination", "route_display"]

    def get_route_display(self, obj):
        return " - ".join(filter(None, [obj.source, obj.via, obj.destination]))


class BankingDetailSerializer(serializers.ModelSerializer):
    account_type_display = serializers.CharField(source="get_account_type_display", read_only=True)
    banking_status_display = serializers.CharField(source="get_banking_status_display", read_only=True)
    verification_status_display = serializers.CharField(
        source="get_verification_status_display",
        read_only=True,
    )

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
            "banking_status",
            "banking_status_display",
            "verification_status",
            "verification_status_display",
            "is_primary",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
