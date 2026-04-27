"""
Operations Views for Fleet Manager API
Comprehensive viewsets matching admin panel functionality
"""

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q, Sum, Count
from datetime import date, timedelta
from rest_framework.views import APIView

from entity.models import Driver, Organization
from operations.models import (
    ConsignmentGroup, Consignment, Shipment, ShipmentExpense, 
    DriverAdvance, ShipmentStatus
)
from .serializers import (
    ConsignmentGroupSerializer, ConsignmentSerializer,
    ShipmentSerializer, ShipmentListSerializer, ShipmentExpenseSerializer,
    DriverAdvanceSerializer, ShipmentStatusSerializer
)


class ConsignmentListCreate(APIView):
    """
    GET  /api/v1/entity/consignments/      -> list (search/filter)
    POST /api/v1/entity/consignments/      -> create
    """

    def get(self, request):
        qs = (
            Consignment.objects
            .select_related(
                "consignor", "consignee",
                "material_type", "weight_unit", "packaging_type",
                "vehicle_type", "freight_mode", "created_by"
            )
            .order_by("-created_at")
        )

        # Simple search/filter
        q = request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(consignment_id__icontains=q) |
                Q(consignor__organization_name__icontains=q) |
                Q(consignee__organization_name__icontains=q)
            )

        consignor_id = request.GET.get("consignor")
        if consignor_id:
            qs = qs.filter(consignor_id=consignor_id)

        consignee_id = request.GET.get("consignee")
        if consignee_id:
            qs = qs.filter(consignee_id=consignee_id)

        date_from = request.GET.get("from")
        date_to = request.GET.get("to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return Response(ConsignmentSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        ser = ConsignmentSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # Build and save so model.save() runs (auto total_freight + consignment_id)
        obj = Consignment(**ser.validated_data)
        # obj.full_clean()  # optional: run model.clean() explicitly
        obj.save()
        return Response(ConsignmentSerializer(obj).data, status=status.HTTP_201_CREATED)


class ConsignmentDetail(APIView):
    """
    GET    /api/v1/entity/consignments/<id>/   -> retrieve
    POST   /api/v1/entity/consignments/<id>/   -> partial update (POST)
    DELETE /api/v1/entity/consignments/<id>/   -> delete
    """

    def get_object(self, pk: int):
        return (
            Consignment.objects
            .select_related(
                "consignor", "consignee",
                "material_type", "weight_unit", "packaging_type",
                "vehicle_type", "freight_mode", "created_by"
            )
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ConsignmentSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ConsignmentSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        for field, value in ser.validated_data.items():
            setattr(obj, field, value)
        # obj.full_clean()  # optional: run model.clean()
        obj.save()          # re-calculates total_freight in model.save()
        return Response(ConsignmentSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ConsignmentGroupListCreate(APIView):
    """
    GET  /api/v1/entity/consignment-groups/     -> list (filters)
    POST /api/v1/entity/consignment-groups/     -> create
    """

    def get(self, request):
        qs = (
            ConsignmentGroup.objects
            .prefetch_related("consignments")
            .select_related("created_by")
            .order_by("-created_at")
        )

        # filters
        q = request.GET.get("q")
        if q:
            qs = qs.filter(Q(group_id__icontains=q))

        planned_from = request.GET.get("planned_from")
        planned_to = request.GET.get("planned_to")
        if planned_from:
            qs = qs.filter(planned_dispatch_date__gte=planned_from)
        if planned_to:
            qs = qs.filter(planned_dispatch_date__lte=planned_to)

        return Response(ConsignmentGroupSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        ser = ConsignmentGroupSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        obj = ser.save()  # create() handles M2M + totals
        return Response(ConsignmentGroupSerializer(obj).data, status=status.HTTP_201_CREATED)


class ConsignmentGroupDetail(APIView):
    """
    GET    /api/v1/entity/consignment-groups/<id>/    -> retrieve
    POST   /api/v1/entity/consignment-groups/<id>/    -> partial update (POST)
    DELETE /api/v1/entity/consignment-groups/<id>/    -> delete
    """

    def get_object(self, pk: int):
        return (
            ConsignmentGroup.objects
            .prefetch_related("consignments")
            .select_related("created_by")
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ConsignmentGroupSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ConsignmentGroupSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        obj = ser.save()  # update() handles M2M + totals (if consignments provided)
        return Response(ConsignmentGroupSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class ShipmentListCreate(APIView):
    """
    GET  /api/v1/entity/shipments/        -> list (filters)
    POST /api/v1/entity/shipments/        -> create
    """

    def get(self, request):
        qs = (
            Shipment.objects
            .select_related(
                "consignment_group", "vehicle", "driver", "co_driver",
                "transporter", "broker", "planned_route", "actual_route", "created_by"
            )
            .order_by("-created_at")
        )

        # Filters
        q = request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(shipment_id__icontains=q) |
                Q(consignment_group__group_id__icontains=q) |
                Q(vehicle__registration_number__icontains=q)
            )

        group_id = request.GET.get("consignment_group")
        if group_id:
            qs = qs.filter(consignment_group_id=group_id)

        vehicle_id = request.GET.get("vehicle")
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)

        driver_id = request.GET.get("driver")
        if driver_id:
            qs = qs.filter(driver_id=driver_id)

        date_from = request.GET.get("from")
        date_to = request.GET.get("to")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return Response(ShipmentSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        ser = ShipmentSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        # Construct then save so your model logic runs (ID gen, totals, distance)
        obj = Shipment(**ser.validated_data)
        obj.save()  # model.save() will set shipment_id, total_distance, total_freight_amount
        return Response(ShipmentSerializer(obj).data, status=status.HTTP_201_CREATED)


class ShipmentDetail(APIView):
    """
    GET    /api/v1/entity/shipments/<id>/   -> retrieve
    POST   /api/v1/entity/shipments/<id>/   -> partial update (POST)
    DELETE /api/v1/entity/shipments/<id>/   -> delete
    """

    def get_object(self, pk: int):
        return (
            Shipment.objects
            .select_related(
                "consignment_group", "vehicle", "driver", "co_driver",
                "transporter", "broker", "planned_route", "actual_route", "created_by"
            )
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShipmentSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ShipmentSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        for field, value in ser.validated_data.items():
            setattr(obj, field, value)
        obj.save()  # recalculates distance & totals; preserves shipment_id
        return Response(ShipmentSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




from django.contrib.contenttypes.models import ContentType



class ShipmentExpenseListCreate(APIView):
    """
    GET  /api/v1/entity/shipment-expenses/       -> list (filters)
    POST /api/v1/entity/shipment-expenses/       -> create (supports multipart for file)
    """

    def get(self, request):
        qs = (
            ShipmentExpense.objects
            .select_related("shipment", "expense_type", "content_type")
            .order_by("-expense_date", "-id")
        )

        # Filters
        shipment_id = request.GET.get("shipment")
        if shipment_id:
            qs = qs.filter(shipment_id=shipment_id)

        expense_type = request.GET.get("expense_type")
        if expense_type:
            qs = qs.filter(expense_type_id=expense_type)

        # Filter by who spent: driver or owner organization
        driver_id = request.GET.get("driver")
        if driver_id:
            ct_driver = ContentType.objects.filter(app_label="entity", model="driver").first()
            if ct_driver:
                qs = qs.filter(content_type=ct_driver, object_id=driver_id)

        owner_id = request.GET.get("owner")
        if owner_id:
            try:
                owner = Organization.objects.get(pk=owner_id, organization_type__internal_value='OWNER')
            except Organization.DoesNotExist:
                qs = qs.none()
            else:
                ct_owner = ContentType.objects.get_for_model(Organization)
                qs = qs.filter(content_type=ct_owner, object_id=owner.id)

        # Date range
        date_from = request.GET.get("from")
        date_to = request.GET.get("to")
        if date_from:
            qs = qs.filter(expense_date__gte=date_from)
        if date_to:
            qs = qs.filter(expense_date__lte=date_to)

        return Response(ShipmentExpenseSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a ShipmentExpense.
        - If uploading 'shipment_expense_document', use multipart/form-data.
        - Otherwise JSON is fine.
        """
        ser = ShipmentExpenseSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        obj = ser.save()
        return Response(ShipmentExpenseSerializer(obj).data, status=status.HTTP_201_CREATED)


class ShipmentExpenseDetail(APIView):
    """
    GET    /api/v1/entity/shipment-expenses/<id>/    -> retrieve
    POST   /api/v1/entity/shipment-expenses/<id>/    -> partial update (POST)
    DELETE /api/v1/entity/shipment-expenses/<id>/    -> delete
    """

    def get_object(self, pk: int):
        return (
            ShipmentExpense.objects
            .select_related("shipment", "expense_type", "content_type")
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShipmentExpenseSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ShipmentExpenseSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        obj = ser.save()
        return Response(ShipmentExpenseSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)





class DriverAdvanceListCreate(APIView):
    """
    GET  /api/v1/entity/driver-advances/         -> list (filters)
    POST /api/v1/entity/driver-advances/         -> create
    """

    def get(self, request):
        qs = (
            DriverAdvance.objects
            .select_related("driver", "shipment")
            .order_by("-date", "-id")
        )

        # filters
        driver_id = request.GET.get("driver")
        if driver_id:
            qs = qs.filter(driver_id=driver_id)

        shipment_id = request.GET.get("shipment")
        if shipment_id:
            qs = qs.filter(shipment_id=shipment_id)

        date_from = request.GET.get("from")
        date_to = request.GET.get("to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        q = request.GET.get("q")
        if q:
            qs = qs.filter(Q(description__icontains=q))

        return Response(DriverAdvanceSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a DriverAdvance.
        - If you want to carry-forward previous unsettled balance automatically,
          pass {"use_carry_forward": true} in the payload.
        """
        use_cf = str(request.data.get("use_carry_forward", "")).lower() in ("1","true","yes")
        if use_cf:
            # use your convenience constructor
            try:
                driver = Driver.objects.get(pk=request.data.get("driver"))
            except Driver.DoesNotExist:
                return Response({"driver": "Invalid driver id."}, status=status.HTTP_400_BAD_REQUEST)
            shipment = None
            if request.data.get("shipment"):
                try:
                    shipment = Shipment.objects.get(pk=request.data.get("shipment"))
                except Shipment.DoesNotExist:
                    return Response({"shipment": "Invalid shipment id."}, status=status.HTTP_400_BAD_REQUEST)
            amount = request.data.get("amount")
            desc = request.data.get("description", "")
            if amount is None:
                return Response({"amount": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
            obj = DriverAdvance.create_driver_advance(driver=driver, shipment=shipment, amount=amount, description=desc)
            return Response(DriverAdvanceSerializer(obj).data, status=status.HTTP_201_CREATED)

        # plain create
        ser = DriverAdvanceSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        obj = ser.save()
        return Response(DriverAdvanceSerializer(obj).data, status=status.HTTP_201_CREATED)


class DriverAdvanceDetail(APIView):
    """
    GET    /api/v1/entity/driver-advances/<id>/   -> retrieve
    POST   /api/v1/entity/driver-advances/<id>/   -> partial update (POST)
    DELETE /api/v1/entity/driver-advances/<id>/   -> delete
    """

    def get_object(self, pk: int):
        return DriverAdvance.objects.select_related("driver", "shipment").filter(pk=pk).first()

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DriverAdvanceSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = DriverAdvanceSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        obj = ser.save()
        return Response(DriverAdvanceSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverAdvanceSettle(APIView):
    """
    POST /api/v1/entity/driver-advances/<id>/settle/
    Runs settle_and_carry_forward() and returns the updated record.
    """

    def post(self, request, pk: int):
        obj = DriverAdvance.objects.filter(pk=pk).first()
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.settle_and_carry_forward()
        return Response(DriverAdvanceSerializer(obj).data, status=status.HTTP_200_OK)


class DriverAdvanceSummary(APIView):
    """
    GET /api/v1/entity/driver-advances/summary?driver=<id>[&shipment=<id>]
    Returns get_driver_summary(driver, shipment)
    """

    def get(self, request):
        driver_id = request.GET.get("driver")
        if not driver_id:
            return Response({"driver": "This query param is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            driver = Driver.objects.get(pk=driver_id)
        except Driver.DoesNotExist:
            return Response({"driver": "Invalid driver id."}, status=status.HTTP_400_BAD_REQUEST)

        shipment = None
        shipment_id = request.GET.get("shipment")
        if shipment_id:
            try:
                shipment = Shipment.objects.get(pk=shipment_id)
            except Shipment.DoesNotExist:
                return Response({"shipment": "Invalid shipment id."}, status=status.HTTP_400_BAD_REQUEST)

        data = DriverAdvance.get_driver_summary(driver, shipment)
        return Response(data, status=status.HTTP_200_OK)

class ShipmentStatusListCreate(APIView):
    """
    GET  /api/v1/entity/shipment-status/       -> list (filters)
    POST /api/v1/entity/shipment-status/       -> create (supports multipart for file)
    """

    def get(self, request):
        qs = (
            ShipmentStatus.objects
            .select_related("shipment", "status", "shipment_doc_type")
            .order_by("-timestamp", "-id")
        )

        # Filters
        shipment_id = request.GET.get("shipment")
        if shipment_id:
            qs = qs.filter(shipment_id=shipment_id)

        status_id = request.GET.get("status")
        if status_id:
            qs = qs.filter(status_id=status_id)

        date_from = request.GET.get("from")
        date_to   = request.GET.get("to")
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        q = request.GET.get("q")
        if q:
            qs = qs.filter(Q(updated_by__icontains=q) | Q(notes__icontains=q))

        return Response(ShipmentStatusSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a ShipmentStatus.
        - If uploading 'shipment_document', use multipart/form-data.
        - Otherwise JSON is fine.
        """
        ser = ShipmentStatusSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        obj = ser.save()
        return Response(ShipmentStatusSerializer(obj).data, status=status.HTTP_201_CREATED)


class ShipmentStatusDetail(APIView):
    """
    GET    /api/v1/entity/shipment-status/<id>/   -> retrieve
    POST   /api/v1/entity/shipment-status/<id>/   -> partial update (POST)
    DELETE /api/v1/entity/shipment-status/<id>/   -> delete
    """

    def get_object(self, pk: int):
        return (
            ShipmentStatus.objects
            .select_related("shipment", "status", "shipment_doc_type")
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShipmentStatusSerializer(obj).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ShipmentStatusSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        obj = ser.save()
        return Response(ShipmentStatusSerializer(obj).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        obj = self.get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
