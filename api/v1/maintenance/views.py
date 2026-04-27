"""
Maintenance API views.
"""

from datetime import date, timedelta

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import MaintenanceRecord, Tyre, TyreTransaction

from .serializers import MaintenanceRecordSerializer, TyreSerializer, TyreTransactionSerializer


class MaintenanceRecordListCreate(APIView):
    def get(self, request):
        queryset = MaintenanceRecord.objects.select_related(
            "vehicle",
            "service_type",
            "items",
            "tyre",
            "vendors",
            "content_type",
        ).order_by("-service_date", "-id")

        vehicle_id = request.GET.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        service_type_id = request.GET.get("service_type")
        if service_type_id:
            queryset = queryset.filter(service_type_id=service_type_id)

        q = request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(vehicle__registration_number__icontains=q)
                | Q(invoice_no__icontains=q)
                | Q(notes__icontains=q)
            )

        serializer = MaintenanceRecordSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MaintenanceRecordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            MaintenanceRecordSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MaintenanceRecordDetail(APIView):
    def get_object(self, pk: int):
        return MaintenanceRecord.objects.select_related(
            "vehicle",
            "service_type",
            "items",
            "tyre",
            "vendors",
            "content_type",
        ).filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            MaintenanceRecordSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = MaintenanceRecordSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            MaintenanceRecordSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaintenanceDueSoon(APIView):
    def get(self, request):
        days = int(request.GET.get("days", 30))
        due_date = date.today() + timedelta(days=days)
        queryset = MaintenanceRecord.objects.filter(
            next_due_date__isnull=False,
            next_due_date__gte=date.today(),
            next_due_date__lte=due_date,
        ).order_by("next_due_date")
        serializer = MaintenanceRecordSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MaintenanceOverdue(APIView):
    def get(self, request):
        queryset = MaintenanceRecord.objects.filter(
            next_due_date__isnull=False,
            next_due_date__lt=date.today(),
        ).order_by("next_due_date")
        serializer = MaintenanceRecordSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TyreListCreate(APIView):
    def get(self, request):
        queryset = Tyre.objects.select_related(
            "brand",
            "model",
            "size",
            "type",
            "tube_type",
            "purchase_type",
        ).order_by("-purchase_date", "-id")

        q = request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(tyreNo__icontains=q)
                | Q(brand__display_value__icontains=q)
                | Q(model__display_value__icontains=q)
            )

        serializer = TyreSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TyreSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TyreSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TyreDetail(APIView):
    def get_object(self, pk: int):
        return Tyre.objects.select_related("brand", "model", "size", "type", "tube_type").filter(pk=pk).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TyreSerializer(instance, context={"request": request}).data, status=status.HTTP_200_OK)

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TyreSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(TyreSerializer(instance, context={"request": request}).data, status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TyreNeedsReplacement(APIView):
    def get(self, request):
        """
        Practical approximation using age threshold because no explicit condition field exists.
        """
        min_age_years = int(request.GET.get("min_age_years", 4))
        tyres = []
        for tyre in Tyre.objects.all():
            age = tyre.calculate_age()
            if age is not None and age >= min_age_years:
                tyres.append(tyre)
        serializer = TyreSerializer(tyres, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TyreTransactionListCreate(APIView):
    def get(self, request):
        queryset = TyreTransaction.objects.select_related(
            "tyre",
            "vehicle",
            "position",
            "transaction_type",
        ).order_by("-transaction_date", "-id")

        tyre_id = request.GET.get("tyre")
        if tyre_id:
            queryset = queryset.filter(tyre_id=tyre_id)

        vehicle_id = request.GET.get("vehicle")
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)

        serializer = TyreTransactionSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TyreTransactionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TyreTransactionSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TyreTransactionDetail(APIView):
    def get_object(self, pk: int):
        return TyreTransaction.objects.select_related("tyre", "vehicle", "position", "transaction_type").filter(
            pk=pk
        ).first()

    def get(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            TyreTransactionSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TyreTransactionSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            TyreTransactionSerializer(instance, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk: int):
        instance = self.get_object(pk)
        if not instance:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
