"""
Entity Views for Fleet Manager API
"""

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from entity.models import (
    Organization, Vehicle, Driver
    # VehicleDocument, DriverDocument, DriverLicense, DriverIdentity
)
from configuration.models import Choice, Location, Route, BankingDetail
from .serializers import (
    OrganizationSerializer,
    VehicleSerializer, VehicleListSerializer,
    DriverSerializer,
    ChoiceSerializer, LocationSerializer, RouteSerializer, BankingDetailSerializer,
    VehicleDocumentSerializer, DriverLicenseSerializer,
)




# @csrf_exempt
# @permission_classes([AllowAny])       # open access
class OrganizationListCreate(APIView):
    """
    GET  /api/organizations/   -> list (optional ?q= search)
    POST /api/organizations/   -> create
    """

    def get(self, request):
        print("hi ranjan")
        qs = Organization.objects.all().order_by("id")
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(organization_name__icontains=q) |
                Q(city__icontains=q) |
                Q(state__icontains=q) |
                Q(contact_person__icontains=q)
            )
        data = OrganizationSerializer(qs, many=True).data
        return Response(data)

    def post(self, request):
        ser = OrganizationSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # Use model.save() so your pincode auto-populate runs
        obj = Organization(**ser.validated_data)
        obj.save()
        return Response(OrganizationSerializer(obj).data, status=status.HTTP_201_CREATED)


class OrganizationDetail(APIView):
    """
    GET    /api/organizations/<id>/  -> retrieve
    POST   /api/organizations/<id>/  -> update (POST as requested)
    DELETE /api/organizations/<id>/  -> delete
    """

    def get_object(self, pk):
        return Organization.objects.filter(pk=pk).first()

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrganizationSerializer(obj).data)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = OrganizationSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # Assign validated fields then save (to trigger auto_populate_from_pincode if pincode changed)
        for field, value in ser.validated_data.items():
            setattr(obj, field, value)
        obj.save()
        return Response(OrganizationSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleListCreate(APIView):
    """
    GET  /api/v1/entity/vehicles/        -> list (search/filter)
    POST /api/v1/entity/vehicles/        -> create
    """

    def get(self, request):
        qs = Vehicle.objects.select_related(
            "owner", "brand_name", "model_name", "truck_type", "engine_type",
            "fuel_type", "body_type", "truck_specification",
            "wheel_count", "load_capacity_tons", "state_registered"
        ).order_by("registration_number")

        # Filters
        q = request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(registration_number__icontains=q) |
                Q(chassis_number__icontains=q)
            )

        owner_id = request.GET.get("owner")
        if owner_id:
            qs = qs.filter(owner_id=owner_id)

        active = request.GET.get("active")
        if active in ("true", "false", "1", "0"):
            qs = qs.filter(is_active=active in ("true", "1"))

        return Response(VehicleSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        ser = VehicleSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        obj = Vehicle(**ser.validated_data)
        # If you need model-level clean() validation to run explicitly:
        # obj.full_clean()
        obj.save()
        return Response(VehicleSerializer(obj).data, status=status.HTTP_201_CREATED)



class VehicleDetail(APIView):
    """
    GET    /api/v1/entity/vehicles/<uuid:id>/   -> retrieve
    POST   /api/v1/entity/vehicles/<uuid:id>/   -> partial update (POST)
    DELETE /api/v1/entity/vehicles/<uuid:id>/   -> delete
    """

    def get_object(self, pk):
        return Vehicle.objects.select_related(
            "owner", "brand_name", "model_name", "truck_type", "engine_type",
            "fuel_type", "body_type", "truck_specification",
            "wheel_count", "load_capacity_tons", "state_registered"
        ).filter(pk=pk).first()

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(VehicleSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = VehicleSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        for field, value in ser.validated_data.items():
            setattr(obj, field, value)
        # obj.full_clean()   # optional to run model clean()
        obj.save()
        return Response(VehicleSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




class DriverListCreate(APIView):
    """
    GET  /api/v1/entity/drivers/        -> list (optional search/filter)
    POST /api/v1/entity/drivers/        -> create (multipart for file upload)
    """

    def get(self, request):
        qs = Driver.objects.select_related("owner").order_by("id")

        # Search across a few fields
        q = request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(middle_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(contact_person__icontains=q) |
                Q(contact_phone__icontains=q) |
                Q(contact_email__icontains=q) |
                Q(city__icontains=q) |
                Q(state__icontains=q) |
                Q(license_number__icontains=q)
            )

        # Filter by owner
        owner_id = request.GET.get("owner") or request.GET.get("owners")
        if owner_id:
            qs = qs.filter(owner_id=owner_id)

        data = DriverSerializer(qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create Driver.
        - If uploading license_document, send multipart/form-data.
        - Otherwise JSON is fine.
        """
        ser = DriverSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # Manual construct so your model.save() runs (which auto-populates addresses)
        obj = Driver(**ser.validated_data)
        obj.save()
        return Response(DriverSerializer(obj).data, status=status.HTTP_201_CREATED)


class DriverDetail(APIView):
    """
    GET    /api/v1/entity/drivers/<id>/   -> retrieve
    POST   /api/v1/entity/drivers/<id>/   -> partial update (POST)
    DELETE /api/v1/entity/drivers/<id>/   -> delete
    """

    def get_object(self, pk: int):
        return Driver.objects.select_related("owner").filter(pk=pk).first()

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DriverSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = DriverSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # Assign only validated fields; model.save() will re-run your pincode auto-population
        for field, value in ser.validated_data.items():
            setattr(obj, field, value)
        obj.save()
        return Response(DriverSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChoiceListView(ListAPIView):
    """
    List view for Choice model filtered by category
    """
    serializer_class = ChoiceSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        category = self.kwargs['category'].upper()
        return Choice.objects.filter(category=category).order_by('display_value')
    
    @extend_schema(
        summary="Get choices by category",
        description="Get list of choices for a specific category",
        parameters=[
            OpenApiParameter('category', str, OpenApiParameter.PATH, description='Choice category'),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ChoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Choice model (read-only)
    """
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    # permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['display_value', 'internal_value']
    ordering_fields = ['category', 'display_value']
    ordering = ['category', 'display_value']
    
    @extend_schema(
        summary="List choices",
        description="Get paginated list of choices with filtering and search"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Location model
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    # permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']
    
    @extend_schema(
        summary="List locations",
        description="Get paginated list of locations with search"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RouteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Route model
    """
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    # permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['source', 'via', 'destination']
    ordering_fields = ['source', 'destination']
    ordering = ['source']
    
    @extend_schema(
        summary="List routes",
        description="Get paginated list of routes with search"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class BankingDetailViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BankingDetail model
    """
    queryset = BankingDetail.objects.all()
    serializer_class = BankingDetailSerializer
    # permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'banking_status', 'verification_status', 'is_primary', 'is_verified']
    search_fields = ['account_holder_name', 'account_number', 'bank_name', 'branch_name', 'ifsc_code']
    ordering_fields = ['account_holder_name', 'bank_name', 'created_at']
    ordering = ['account_holder_name']
    
    @extend_schema(
        summary="List banking details",
        description="Get paginated list of banking details with filtering and search"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
