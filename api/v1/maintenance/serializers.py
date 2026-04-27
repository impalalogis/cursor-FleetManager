"""
Maintenance Serializers for Fleet Manager API
"""

from rest_framework import serializers
from maintenance.models import MaintenanceRecord, TyreTransaction, Tyre
from entity.models import Vehicle
# from setting.models import Choice


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for MaintenanceRecord model"""
    vehicle_number = serializers.CharField(source='vehicle.registration_number', read_only=True)
    maintenance_type_display = serializers.CharField(source='maintenance_type.display_value', read_only=True)
    
    class Meta:
        model = MaintenanceRecord
        fields = [
            'id', 'vehicle', 'vehicle_number', 'maintenance_date',
            'maintenance_type', 'maintenance_type_display', 'cost',
            'description', 'odometer_reading', 'next_service_date',
            'next_service_odometer', 'service_provider', 'invoice_number',
            'parts_replaced', 'notes', 'created_at', 'updated_at'
        ]


class TyreSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Tyre model"""
    vehicle_number = serializers.CharField(source='vehicle.registration_number', read_only=True)
    tyre_size_display = serializers.CharField(source='tyre_size.display_value', read_only=True)
    tyre_brand_display = serializers.CharField(source='tyre_brand.display_value', read_only=True)
    
    class Meta:
        model = Tyre
        fields = [
            'id', 'vehicle', 'vehicle_number', 'position', 'tyre_size',
            'tyre_size_display', 'tyre_brand', 'tyre_brand_display',
            'purchase_date', 'purchase_price', 'installation_date',
            'installation_odometer', 'current_condition', 'notes',
            'created_at', 'updated_at'
        ]


class TyreTransactionSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for TyreTransaction model"""
    tyre_vehicle = serializers.CharField(source='tyre.vehicle.registration_number', read_only=True)
    tyre_position = serializers.CharField(source='tyre.position', read_only=True)
    transaction_type_display = serializers.CharField(source='transaction_type.display_value', read_only=True)
    
    class Meta:
        model = TyreTransaction
        fields = [
            'id', 'tyre', 'tyre_vehicle', 'tyre_position', 'transaction_date',
            'transaction_type', 'transaction_type_display', 'odometer_reading',
            'cost', 'description', 'invoice_number', 'service_provider',
            'notes', 'created_at', 'updated_at'
        ]