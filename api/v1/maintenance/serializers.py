"""
Maintenance API serializers.
"""

from rest_framework import serializers

from maintenance.models import MaintenanceRecord, Tyre, TyreTransaction


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRecord
        fields = "__all__"


class TyreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tyre
        fields = "__all__"


class TyreTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TyreTransaction
        fields = "__all__"

