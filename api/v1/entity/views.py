"""
Entity API views.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from configuration.models import BankingDetail, Choice, Location, Route
from entity.models import (
    Driver,
    DriverDocument,
    Organization,
    OrganizationDocument,
    Vehicle,
    VehicleDocument,
)

from .serializers import (
    BankingDetailSerializer,
    ChoiceSerializer,
    DriverDocumentSerializer,
    DriverSerializer,
    LocationSerializer,
    OrganizationDocumentSerializer,
    OrganizationSerializer,
    RouteSerializer,
    VehicleDocumentSerializer,
    VehicleSerializer,
)


class OrganizationListCreate(APIView):
    def get(self, request):
        queryset = Organization.objects.select_related("organization_type", "location").order_by("organization_name")
        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(
                Q(organization_name__icontains=q)
                | Q(city__icontains=q)
                | Q(state__icontains=q)
                | Q(contact_person__icontains=q)
            )
        org_type = request.query_params.get("organization_type")
        if org_type:
            queryset = queryset.filter(organization_type_id=org_type)
        serializer = OrganizationSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OrganizationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            OrganizationSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationDetail(APIView):
    def get_object(self, pk):
        return Organization.objects.select_related("organization_type", "location").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            OrganizationSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrganizationSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            OrganizationSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleListCreate(APIView):
    def get(self, request):
        queryset = Vehicle.objects.select_related(
            "owner",
            "brand_name",
            "model_name",
            "truck_type",
            "engine_type",
            "fuel_type",
            "body_type",
            "truck_specification",
            "wheel_count",
            "load_capacity_tons",
            "state_registered",
        ).order_by("registration_number")

        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(
                Q(registration_number__icontains=q) | Q(chassis_number__icontains=q)
            )
        owner_id = request.query_params.get("owner")
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        active = request.query_params.get("active")
        if active in {"true", "false", "1", "0"}:
            queryset = queryset.filter(is_active=active in {"true", "1"})

        serializer = VehicleSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = VehicleSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            VehicleSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class VehicleDetail(APIView):
    def get_object(self, pk):
        return Vehicle.objects.select_related("owner").filter(pk=pk).first()

    def get(self, request, pk):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            VehicleSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            VehicleSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverListCreate(APIView):
    def get(self, request):
        queryset = Driver.objects.select_related("owner").order_by("id")
        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(
                Q(first_name__icontains=q)
                | Q(middle_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(contact_phone__icontains=q)
                | Q(contact_email__icontains=q)
                | Q(city__icontains=q)
                | Q(state__icontains=q)
                | Q(license_number__icontains=q)
            )

        owner_id = request.query_params.get("owner")
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        active = request.query_params.get("active")
        if active in {"true", "false", "1", "0"}:
            queryset = queryset.filter(is_active=active in {"true", "1"})

        serializer = DriverSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DriverSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DriverSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DriverDetail(APIView):
    def get_object(self, pk):
        return Driver.objects.select_related("owner").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            DriverSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DriverSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DriverSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverFinancialSummary(APIView):
    """
    API parity for Driver admin financial summary/ledger helpers.
    """

    def get(self, request, pk: int):
        driver = get_object_or_404(Driver, pk=pk)
        return Response(driver.driver_advance_breakdown(), status=status.HTTP_200_OK)


class DriverDocumentListCreate(APIView):
    def get(self, request):
        queryset = DriverDocument.objects.select_related("driver", "doc_type").order_by("-uploaded_at")
        driver_id = request.query_params.get("driver")
        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)
        doc_type = request.query_params.get("doc_type")
        if doc_type:
            queryset = queryset.filter(doc_type_id=doc_type)
        serializer = DriverDocumentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = DriverDocumentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DriverDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DriverDocumentDetail(APIView):
    def get_object(self, pk):
        return DriverDocument.objects.select_related("driver", "doc_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            DriverDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DriverDocumentSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            DriverDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationDocumentListCreate(APIView):
    def get(self, request):
        queryset = OrganizationDocument.objects.select_related("organization", "doc_type").order_by("-uploaded_at")
        organization_id = request.query_params.get("organization")
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        doc_type = request.query_params.get("doc_type")
        if doc_type:
            queryset = queryset.filter(doc_type_id=doc_type)
        serializer = OrganizationDocumentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OrganizationDocumentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            OrganizationDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationDocumentDetail(APIView):
    def get_object(self, pk):
        return OrganizationDocument.objects.select_related("organization", "doc_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            OrganizationDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrganizationDocumentSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            OrganizationDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleDocumentListCreate(APIView):
    def get(self, request):
        queryset = VehicleDocument.objects.select_related("vehicle", "doc_type").order_by("-uploaded_at")
        vehicle_id = request.query_params.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        doc_type = request.query_params.get("doc_type")
        if doc_type:
            queryset = queryset.filter(doc_type_id=doc_type)
        serializer = VehicleDocumentSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = VehicleDocumentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            VehicleDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class VehicleDocumentDetail(APIView):
    def get_object(self, pk):
        return VehicleDocument.objects.select_related("vehicle", "doc_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            VehicleDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleDocumentSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            VehicleDocumentSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Choice.objects.all().order_by("category", "display_value")
    serializer_class = ChoiceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category.upper())
        return queryset


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all().order_by("name")
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all().order_by("source")
    serializer_class = RouteSerializer
    permission_classes = [AllowAny]


class BankingDetailViewSet(viewsets.ModelViewSet):
    queryset = BankingDetail.objects.all().order_by("account_holder_name")
    serializer_class = BankingDetailSerializer
    permission_classes = [AllowAny]
