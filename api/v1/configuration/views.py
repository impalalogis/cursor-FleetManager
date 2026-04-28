"""
Configuration API viewsets.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response

from api.utils import BulkModelViewSet, StandardResultsSetPagination
from configuration.models import BankingDetail, Choice, Location, PostalInfo, Route

from .serializers import BankingDetailSerializer, ChoiceSerializer, LocationSerializer, PostalInfoSerializer, RouteSerializer


class BaseConfigurationViewSet(BulkModelViewSet):
    authentication_classes = []
    permission_classes = []
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class ChoiceViewSet(BaseConfigurationViewSet):
    queryset = Choice.objects.all().order_by("category", "display_value")
    serializer_class = ChoiceSerializer
    filterset_fields = ["category"]
    search_fields = ["category", "internal_value", "display_value"]
    ordering_fields = ["category", "internal_value", "display_value", "id"]


class LocationViewSet(BaseConfigurationViewSet):
    queryset = Location.objects.all().order_by("name")
    serializer_class = LocationSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "id"]


class RouteViewSet(BaseConfigurationViewSet):
    queryset = Route.objects.all().order_by("source", "via", "destination")
    serializer_class = RouteSerializer
    search_fields = ["source", "via", "destination"]
    ordering_fields = ["source", "via", "destination", "id"]


class BankingDetailViewSet(BaseConfigurationViewSet):
    queryset = BankingDetail.objects.all().order_by("account_holder_name")
    serializer_class = BankingDetailSerializer
    filterset_fields = ["account_type"]
    search_fields = ["account_holder_name", "bank_name", "account_number", "ifsc_code"]
    ordering_fields = ["account_holder_name", "bank_name", "id"]


class PostalInfoViewSet(BaseConfigurationViewSet):
    queryset = PostalInfo.objects.all().order_by("pincode")
    serializer_class = PostalInfoSerializer
    filterset_fields = ["pincode", "statename", "Districtname", "Taluk"]
    search_fields = ["pincode", "officename", "Taluk", "Districtname", "statename"]
    ordering_fields = ["pincode", "statename", "Districtname", "id"]

    @action(detail=False, methods=["get"], url_path=r"(?P<pincode>\d+)/lookup")
    def lookup(self, request, pincode=None):
        details = PostalInfo.get_postal_details(int(pincode))
        if not details:
            return Response({"detail": "Postal info not found."}, status=404)
        return Response(details)
