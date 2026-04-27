"""
Entity Serializers for Fleet Manager API
"""
from rest_framework import serializers
from entity.models import (

    Organization, Vehicle, Driver,
    # VehicleDocument, DriverDocument, DriverLicense, DriverIdentity
)
from configuration.models import Choice, Location, Route, BankingDetail

class ChoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Choice model (used in dropdowns)
    """
    class Meta:
        model = Choice
        fields = ['id', 'category', 'display_value', 'internal_value']


class OrganizationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "organization_name",
            "organization_type",
            "notes",
            # AddressMixin
            "address_line_1", "address_line_2", "locality", "city",
            "district", "state", "country", "pincode", "landmark",
            # ContactMixin
            "contact_person", "contact_phone", "contact_email",
            "phone_number", "email",
            # BusinessEntityMixin
            "GST_NO", "GST_document",
        ]

class OrganizationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for organization listing
    """
    organization_type_display = serializers.CharField(source='organization_type.display_value', read_only=True)

    class Meta:
        model = Organization
        fields = [
            'id', 'organization_name', 'organization_type', 'organization_type_display',
            'phone_number', 'contact_person', 'email', 'city', 'state'
        ]

class VehicleSerializer(serializers.ModelSerializer):
    # Read-only helpers
    id = serializers.UUIDField(read_only=True)
    maintenance_due = serializers.SerializerMethodField()
    compliance_status = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            # registration/identity
            "registration_number", "chassis_number",
            # choice FKs
            "brand_name", "model_name", "truck_type", "engine_type",
            "fuel_type", "body_type", "truck_specification",
            "wheel_count", "load_capacity_tons",
            # compliance/maintenance
            "maintenance_due_date", "insurance_expiry",
            "fitness_certificate_expiry", "pollution_certificate_expiry",
            # ownership
            "owner", "state_registered",
            # status
            "is_active",
            # computed
            "maintenance_due", "compliance_status", "summary",
        ]

    def get_maintenance_due(self, obj):
        return bool(getattr(obj, "is_maintenance_due", False))

    def get_compliance_status(self, obj):
        try:
            return obj.compliance_status
        except Exception:
            return {}

    def get_summary(self, obj):
        s = lambda x: str(x) if x is not None else None
        return {
            "id": str(obj.id),
            "registration_number": obj.registration_number,
            "chassis_number": obj.chassis_number,
            "brand_model": " ".join(filter(None, [s(obj.brand_name), s(obj.model_name)])).strip(),
            "specifications": {
                "truck_type": s(obj.truck_type),
                "engine_type": s(obj.engine_type),
                "fuel_type": s(obj.fuel_type),
                "body_type": s(obj.body_type),
                "wheel_count": s(obj.wheel_count),
                "load_capacity_tons": s(obj.load_capacity_tons),
            },
            "owner": obj.owner_id,   # or s(obj.owner) if you want the name
            "is_active": obj.is_active,
        }

    # (Optional) add strict FK category checks — tell me and I’ll add validators

class VehicleListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for vehicle listing
    """
    brand_name_display = serializers.CharField(source='brand_name.display_value', read_only=True)
    model_name_display = serializers.CharField(source='model_name.display_value', read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id', 'registration_number', 'brand_name', 'brand_name_display',
            'model_name', 'model_name_display', 'owner', 'owner_name'
        ]
        
    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.organization_name
        return None


class DriverSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    # Computed/read-only
    age = serializers.IntegerField(read_only=True)                  # from PersonMixin
    full_name = serializers.CharField(read_only=True)               # from PersonMixin
    formatted_address = serializers.SerializerMethodField()         # from AddressMixin
    license_status = serializers.SerializerMethodField()            # from model property
    current_vehicle_id = serializers.SerializerMethodField()        # expose vehicle id if any

    class Meta:
        model = Driver
        fields = [
            "id",
            # PersonMixin
            "title", "first_name", "middle_name", "last_name",
            "date_of_birth", "gender",
            # ContactMixin
            "contact_person", "contact_phone", "contact_email",
            "phone_number", "email",
            # AddressMixin
            "address_line_1", "address_line_2", "locality", "city",
            "district", "state", "country", "pincode", "landmark",
            # REQUIRED relation
            "owner",

            # Driver-specific
            "license_number", "license_document", "license_expiry",

            # Family address set
            "family_name", "family_address_line_1", "family_address_line_2",
            "family_locality", "family_city", "family_district",
            "family_state", "family_country", "family_pincode",
            "family_landmark", "family_phone_number",

            # Computed
            "age", "full_name", "formatted_address", "license_status", "current_vehicle_id",
        ]

    def get_formatted_address(self, obj):
        return obj.get_formatted_address() if hasattr(obj, "get_formatted_address") else None

    def get_license_status(self, obj):
        try:
            return obj.license_status
        except Exception:
            return None

    def get_current_vehicle_id(self, obj):
        v = getattr(obj, "current_vehicle", None)
        return v.id if v else None

    def validate(self, attrs):
        # owner is required by model (on_delete=PROTECT), but make the 400 nicer:
        owner = attrs.get("owner") if not self.instance else attrs.get("owner", getattr(self.instance, "owner", None))
        if owner is None:
            raise serializers.ValidationError({"owner": "This field is required (driver must belong to an owner organization)."})
        owner_type = getattr(owner, "organization_type_code", None)
        if owner_type != 'OWNER':
            raise serializers.ValidationError({"owner": "Selected organization must be of type OWNER."})
        return attrs


#class Meta:
class VehicleDocumentSerializer(serializers.Serializer):
    """
    Placeholder serializer for Vehicle Document model (not implemented yet)
    """
    pass

class DriverDocumentSerializer(serializers.Serializer):
    """
    Placeholder serializer for Driver Document model (not implemented yet)
    """
    pass

class DriverLicenseSerializer(serializers.Serializer):
    """
    Placeholder serializer for Driver License model (not implemented yet)
    """
    pass

class DriverIdentitySerializer(serializers.Serializer):
    """
    Placeholder serializer for Driver Identity model (not implemented yet)
    """

    pass


class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for Location model
    """
    class Meta:
        model = Location
        fields = ['id', 'name']


class RouteSerializer(serializers.ModelSerializer):
    """
    Serializer for Route model
    """
    route_display = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'source', 'via', 'destination', 'route_display']

    def get_route_display(self, obj):
        """Get formatted route display"""
        parts = [obj.source, obj.via, obj.destination]
        return ' - '.join(filter(None, parts))


class BankingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for BankingDetail model
    """
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    banking_status_display = serializers.CharField(source='get_banking_status_display', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)

    class Meta:
        model = BankingDetail
        fields = [
            'id', 'account_holder_name', 'account_number', 'bank_name', 'branch_name',
            'ifsc_code', 'account_type', 'account_type_display', 'banking_status',
            'banking_status_display', 'verification_status', 'verification_status_display',
            'is_primary', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

