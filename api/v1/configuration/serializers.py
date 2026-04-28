"""
Configuration API serializers.
"""

from rest_framework import serializers

from configuration.models import BankingDetail, Choice, Location, PostalInfo, Route


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"


class BankingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankingDetail
        fields = "__all__"


class PostalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostalInfo
        fields = "__all__"

